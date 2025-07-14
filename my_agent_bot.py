import os
import re
import uuid
import logging
import asyncpg
from datetime import datetime, timezone
from dotenv import load_dotenv
from docx import Document
import PyPDF2
from typing import Optional

import chainlit as cl
from chainlit.context import context
from chainlit.types import AskFileResponse

from langchain_core.prompts import PromptTemplate
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain_community.chat_message_histories import ChatMessageHistory

from langchain_openai import ChatOpenAI

# Define database utility functions directly in this file to avoid import issues
# Version: 2.1 - Fixed Railway PostgreSQL schema compatibility
async def save_session_to_db(student_id, current_step_index, total_interactions=None, last_message_content=None):
    """Save the current session state to the database."""
    try:
        # Get database URL from environment variable
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logging.error("DATABASE_URL environment variable not set")
            return False

        conn = await asyncpg.connect(database_url)
        logging.info("Connected to database successfully")

        # Insert or update the session data
        # Use NOW() from PostgreSQL instead of Python datetime to avoid timezone issues
        update_fields = ["current_step_index = $2", "last_updated = NOW()"]
        params = [student_id, current_step_index]

        # Add total_interactions if provided
        if total_interactions is not None:
            update_fields.append("total_interactions = $3")
            params.append(total_interactions)

        # Add last_message_content if provided
        if last_message_content is not None:
            update_fields.append("last_message_content = $" + str(len(params) + 1))
            params.append(last_message_content)

        # Build the SQL query
        query = f"""
            INSERT INTO student_sessions (student_id, current_step_index, last_updated)
            VALUES ($1, $2, NOW())
            ON CONFLICT (student_id)
            DO UPDATE SET
                {", ".join(update_fields)}
        """

        await conn.execute(query, *params)

        await conn.close()
        logging.info(f"Session saved for student {student_id}")
        return True
    except Exception as e:
        logging.error(f"Error saving session: {e}")
        return False

async def save_pitch_evaluation(student_id, step_name, score, feedback):
    """Save a pitch evaluation to the database."""
    try:
        # Get database URL from environment variable
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logging.error("DATABASE_URL environment variable not set")
            return False

        conn = await asyncpg.connect(database_url)
        logging.info("Connected to database successfully")

        # Insert the evaluation data
        await conn.execute("""
            INSERT INTO pitch_evaluations (student_id, step_name, score, feedback, evaluation_date)
            VALUES ($1, $2, $3, $4, NOW())
        """, student_id, step_name, score, feedback)

        # Update the student's session to increment completed_steps
        await conn.execute("""
            UPDATE student_sessions
            SET completed_steps = COALESCE(completed_steps, 0) + 1
            WHERE student_id = $1
        """, student_id)

        await conn.close()
        logging.info(f"Pitch evaluation saved for student {student_id}, step {step_name}")
        return True
    except Exception as e:
        logging.error(f"Error saving pitch evaluation: {e}")
        return False

async def increment_interactions(student_id):
    """Increment the total_interactions counter for a student."""
    try:
        # Get database URL from environment variable
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logging.error("DATABASE_URL environment variable not set")
            return False

        conn = await asyncpg.connect(database_url)
        logging.info("Connected to database successfully")

        # Update the student's session to increment total_interactions
        await conn.execute("""
            UPDATE student_sessions
            SET total_interactions = COALESCE(total_interactions, 0) + 1
            WHERE student_id = $1
        """, student_id)

        await conn.close()
        logging.info(f"Incremented interactions for student {student_id}")
        return True
    except Exception as e:
        logging.error(f"Error incrementing interactions: {e}")
        return False

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# --- Utility Functions ---
def extract_text_from_file(file: cl.File):
    """Extract text from PDF or DOCX file."""
    try:
        if file.name.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(file.path)
            text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
        elif file.name.endswith(".docx"):
            doc = Document(file.path)
            text = "\n".join([para.text for para in doc.paragraphs])
        else:
            logging.warning(f"❌ Unsupported file type: {file.name}")
            return None
        return text
    except Exception as e:
        logging.error(f"❌ Error extracting text from {file.name}: {e}")
        return None

def flatten_messages(messages: list[BaseMessage]):
    """Safely converts list of messages to a formatted string."""
    return "\n".join([m.content for m in messages if hasattr(m, "content") and isinstance(m.content, str)])

# --- LLM Setup ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.7,
    openai_api_key=api_key,
    streaming=True
)

class StreamHandler(BaseCallbackHandler):
    """Callback handler for streaming LLM responses."""
    def __init__(self, message_id: str):
        self.message_id = message_id
        self.content = ""
        self.msg = None

    async def on_llm_new_token(self, token: str, **kwargs):
        self.content += token
        if not self.msg:
            self.msg = cl.Message(content=self.content, id=self.message_id)
            await self.msg.send()
        else:
            self.msg.content = self.content
            await self.msg.update()

    async def on_llm_error(self, error: BaseException, **kwargs):
        error_msg = f"Error: {error}"
        if not self.msg:
            self.msg = cl.Message(content=error_msg, id=self.message_id)
            await self.msg.send()
        else:
            self.msg.content = error_msg
            await self.msg.update()

# --- Elevator Pitch Steps ---
pitch_steps = [
    "Identify the Target Audience",
    "Define the Problem/Need",
    "Introduce the Product/Service",
    "Highlight the Key Differentiator",
    "End with a Strong Closing Statement"
]

# --- Define AI Agents ---
PROMPTS = {
    "mentor": PromptTemplate(
        input_variables=["context", "question", "current_step", "pitch_steps", "current_step_index", "total_steps"],
        template="""
        [SYSTEM MESSAGE]
        You are the Mentor Agent, guiding students through creating an elevator pitch.

        🚀 **Current Step ({current_step_index}/{total_steps}):** {current_step}

        📋 **All Steps:**
        {pitch_steps}

        🔍 **BALANCED GUIDANCE MODE** 🔍

        You MUST follow these guidelines:
        - Ask 1-2 focused questions for each step that are appropriate for undergraduate students
        - Be encouraging and supportive rather than challenging
        - Keep your responses concise and practical (no more than 3-4 paragraphs)
        - If the student types "/next" or says they want to move to the next step, add "[STEP_COMPLETED]" to your response
        - Add "[STEP_COMPLETED]" after 2-3 meaningful exchanges if the student has provided reasonable answers
        - Avoid overwhelming the student with too many questions at once
        - Focus on practical advice rather than theoretical concepts
        - If the student seems confused, simplify your guidance

        **Current Progress:**
        {context}

        **Student Question:**
        {question}

        **Mentor's Guided Response:**
        """
    ),
    "peer": PromptTemplate(
        input_variables=["context", "question"],
        template="""
        [SYSTEM MESSAGE]
        You are the Peer Agent, just a regular student helping another student brainstorm an elevator pitch.
    - Keep the conversation chill, friendly, and informal.
    - You are NOT an expert—don't give structured frameworks or detailed feedback.
    - Instead, react naturally and ask simple, curious questions.
    - If the user asks "Who are you?", respond: "Hey! I'm your Peer Agent, just a fellow student here to bounce ideas with you. No pressure, let's figure this out together!"

        **Conversation History:**
        {context}

        **Student Message:**
        {question}

        **Peer's Thoughtful Response:**
        """
    ),
    "progress": PromptTemplate(
        input_variables=["context", "question", "student_progress", "time_spent"],
        template="""
        [SYSTEM MESSAGE]
        You are the Progress Agent, tracking the student's progress through their elevator pitch creation.
        - Track student step progress and time spent.
        - Retrieve stored progress from the database.

        ✅ **Current Step:** {student_progress}
        ⏳ **Time Spent on This Step:** {time_spent} seconds

        **Conversation History:**
        {context}

        **Student Message:**
        {question}

        **Progress Tracking Response:**
        """
    ),
    "eval": PromptTemplate(
        input_variables=["pitch"],
        template="""
        [SYSTEM MESSAGE]
        You are the Evaluator Agent, responsible for reviewing and grading elevator pitches.
        - Score each pitch out of 10 based on:
          1️⃣ **Clarity**
          2️⃣ **Engagement**
          3️⃣ **Persuasiveness**
          4️⃣ **Structure**
          5️⃣ **Effectiveness**

        - Provide structured feedback on strengths & areas for improvement.

        **Student Pitch:**
        {pitch}

        **Evaluation Feedback & Score:**
        """
    )
}

# --- Create LLM Chains for Agents ---
agents = {agent: PROMPTS[agent] | llm for agent in PROMPTS.keys()}

@cl.on_chat_start
async def start():
    """Initialize chat session and welcome message."""
    # Generate a new student ID for each session
    import random
    student_id = str(random.randint(10000000, 99999999))
    await cl.Message(content=f"You've been assigned Student ID: #{student_id}\n\nIMPORTANT: Please write down this ID for your records. You'll need it to identify your data in the experiment.").send()

    # Initialize session with the new ID
    cl.user_session.set("student_id", student_id)
    cl.user_session.set("current_step_index", 0)
    cl.user_session.set("current_step", pitch_steps[0])
    logging.info(f"New student assigned ID: {student_id}")

    # Initialize basic session variables
    cl.user_session.set("agent", "mentor")
    cl.user_session.set("pitch_steps", pitch_steps)  # Store pitch_steps in user session
    cl.user_session.set("total_steps", len(pitch_steps))

    # Initialize step interaction counter
    cl.user_session.set("step_interactions", {})  # Dictionary to track interactions per step

    # Initialize timer
    cl.user_session.set("start_time", datetime.now(timezone.utc))

    # Save initial session to database
    try:
        # Attempt to save session, but don't worry if it fails
        save_result = await save_session_to_db(student_id, cl.user_session.get("current_step_index", 0))
        if not save_result:
            logging.info("Initial session not saved to database, continuing with local session only")
    except Exception as e:
        logging.error(f"Error saving initial session: {e}")
        # Continue with the session even if database save fails

    # Send welcome message with student ID
    await cl.Message(content=f"🎓 **Welcome to the AI Elevator Pitch Tutor, Student #{student_id}!** 🏆\n\n"
                            "🤖 This tutor is powered by **four AI agents**:\n"
                            "- 🧑‍🏫 **Mentor Agent** → Guides you step-by-step with practical feedback.\n"
                            "- 👥 **Peer Agent** → Thinks with you like a fellow student.\n"
                            "- 📈 **Progress Agent** → Tracks your step-by-step progress.\n"
                            "- 📝 **Evaluator Agent** → Reviews and scores your final pitch.\n\n"
                            "💡 **Commands:**\n"
                            "- `/next` - Move to the next step when you're ready\n"
                            "- `/progress` - Check your current progress and time spent\n"
                            "- `/mentor`, `/peer`, `/progress`, `/eval` - Switch between agents\n"
                            "- `/upload` - Submit your final pitch\n\n"
                            "💾 **Session Information:**\n"
                            f"- Your Student ID is: **{student_id}**\n"
                            "- Your progress is automatically saved as you complete steps\n\n"
                            "❗ **IMPORTANT:** The tutor will guide you through each step with focused questions. When you feel ready to move on, simply type `/next` to proceed to the next step.\n\n"
                            f"🔹 You're now talking to the **Mentor Agent**.").send()

# This function is now defined at the top of the file

@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages and agent interactions."""
    # Get student ID from session
    student_id = cl.user_session.get("student_id")

    # Check if student ID exists
    if not student_id:
        await cl.Message(content="⚠️ **Session Error**\n\n"
                                "Your session appears to have expired or you haven't logged in.\n"
                                "Please refresh the page and enter your Student ID again.").send()
        return

    # Get other session variables
    selected_agent = cl.user_session.get("agent")
    pitch_steps = cl.user_session.get("pitch_steps")
    current_step_index = cl.user_session.get("current_step_index", 0)
    current_step = cl.user_session.get("current_step", pitch_steps[0] if pitch_steps else "initial")
    total_steps = cl.user_session.get("total_steps", len(pitch_steps))
    start_time = cl.user_session.get("start_time", datetime.now(timezone.utc))

    # Calculate elapsed time
    elapsed_time = (datetime.now(timezone.utc) - start_time).total_seconds() / 60  # in minutes
    progress_percentage = int((current_step_index / total_steps) * 100) if total_steps > 0 else 0

    # Handle progress check command
    if message.content.lower() == "/progress":
        # Get interaction count for the current step
        step_interactions = cl.user_session.get("step_interactions", {})
        current_step_key = f"step_{current_step_index}"
        interaction_count = step_interactions.get(current_step_key, 0)

        # Calculate remaining interactions needed
        remaining = max(0, 2 - interaction_count)
        interaction_info = f"You need at least 2 interactions per step (need {remaining} more) or type /next to proceed."

        await cl.Message(content=f"⏱️ **Time elapsed:** {elapsed_time:.1f} minutes\n"
                                f"📊 **Progress:** {progress_percentage}% complete\n"
                                f"📝 **Current step:** {current_step} ({current_step_index + 1}/{total_steps})\n"
                                f"💬 **Step interactions:** {interaction_count} ({interaction_info})\n"
                                f"🆔 **Student ID:** {student_id} (IMPORTANT: Write down this ID for your records!)").send()
        return

    # Handle file upload command
    if message.content.lower() == "/upload":
        files = await cl.AskFileMessage(
            content="Please upload your pitch document (PDF or DOCX)",
            accept=["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
            max_size_mb=20,
            timeout=180,
        ).send()

        if files:
            await process_file(files[0])
        else:
            await cl.Message(content=f"No file was uploaded. Try again with `/upload` command.\n\nIMPORTANT: Remember your Student ID: #{student_id} - you'll need it to identify your data after the experiment.").send()
        return

    # Handle agent switching commands
    if message.content.lower() in ["/mentor", "/peer", "/progress", "/eval"]:
        new_agent = message.content.lower()[1:]
        cl.user_session.set("agent", new_agent)
        await cl.Message(content=f"🔹 Switched to **{new_agent.capitalize()} Agent**\n\nRemember your Student ID: #{student_id}").send()
        return

    try:
        # Create a message placeholder with metadata
        msg = cl.Message(content="")

        # Add metadata to the message for tracking
        msg.metadata = {
            "student_id": student_id,
            "agent": selected_agent,
            "current_step": current_step,
            "step_index": current_step_index,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Send the message
        await msg.send()

        # Set up the streaming callback
        callback = StreamHandler(msg.id)

        # Create a new instance of the LLM with the callbacks
        llm_with_callbacks = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            openai_api_key=api_key,
            streaming=True,
            callbacks=[callback]
        )

        # Create the chain with the new LLM instance
        chain = PROMPTS[selected_agent] | llm_with_callbacks

        # Prepare formatted pitch steps for the prompt
        formatted_pitch_steps = "\n".join([f"{i+1}. {step}" for i, step in enumerate(pitch_steps)])

        # Prepare chain input with all necessary variables
        chain_input = {
            "context": flatten_messages(cl.user_session.get(f"{selected_agent}_memory", ChatMessageHistory()).messages),
            "question": message.content,
            "current_step": current_step,
            "current_step_index": current_step_index + 1,  # Make it 1-indexed for display
            "total_steps": total_steps,
            "pitch_steps": formatted_pitch_steps,
            "student_progress": cl.user_session.get("student_progress", "Not started"),
            "time_spent": elapsed_time,
            "pitch": message.content
        }

        # Log the agent being used
        logging.info(f"Sending to {selected_agent} agent")

        # The response will be streamed through the callback
        await chain.ainvoke(chain_input)

        # Get the final content from the callback
        ai_text = callback.content

        # Track interactions for the current step if this is the Mentor Agent
        if selected_agent == "mentor":
            step_interactions = cl.user_session.get("step_interactions", {})
            current_step_key = f"step_{current_step_index}"
            if current_step_key not in step_interactions:
                step_interactions[current_step_key] = 0
            step_interactions[current_step_key] += 1
            cl.user_session.set("step_interactions", step_interactions)

            # Log the interaction count
            logging.info(f"Step {current_step_index} ({current_step}) interaction count: {step_interactions[current_step_key]}")

        # Check if the response indicates the student has completed the current step
        if "[STEP_COMPLETED]" in ai_text and selected_agent == "mentor":
            # Get the last user message to check if it has actual content
            last_user_message = message.content.strip().lower()

            # Log the step completion marker detection
            logging.info(f"[STEP_COMPLETED] marker detected for student {student_id}")

            # Skip advancement if the user message is too short or just about mode switching
            skip_advancement = False
            advancement_reason = None

            # Get the interaction count for the current step
            step_interactions = cl.user_session.get("step_interactions", {})
            current_step_key = f"step_{current_step_index}"
            interaction_count = step_interactions.get(current_step_key, 0)

            # Check if the user explicitly requested to move to the next step
            if last_user_message == "/next" or "next step" in last_user_message:
                skip_advancement = False
                advancement_reason = "user requested next step"
                logging.info(f"User requested to move to next step")
            # Check for minimum interactions (at least 2)
            elif interaction_count < 2:
                skip_advancement = True
                advancement_reason = f"insufficient interactions (only {interaction_count})"
                logging.info(f"Preventing premature step advancement: only {interaction_count} interactions")
            # Check message length for very short messages
            elif len(last_user_message) < 10 and last_user_message != "/next":  # Message is too short to be meaningful content
                skip_advancement = True
                advancement_reason = "message too short"
            # Check for common greetings (but allow "next" as a valid command)
            common_phrases = ["hi", "hello", "hey", "start", "begin"]
            if any(phrase == last_user_message for phrase in common_phrases):
                skip_advancement = True
                advancement_reason = "message contains only greeting"

            # Log the advancement decision
            if skip_advancement:
                logging.info(f"Skipping step advancement for student {student_id}: {advancement_reason}")
            else:
                logging.info(f"Step advancement approved for student {student_id} with {interaction_count} interactions")

            # Remove the marker from the displayed text
            ai_text = ai_text.replace("[STEP_COMPLETED]", "")

            # Update the message with the cleaned text
            callback.content = ai_text
            callback.msg.content = ai_text
            await callback.msg.update()

            # Only advance if we have meaningful content
            if not skip_advancement:
                # Move to the next step if not at the end
                if current_step_index < total_steps - 1:
                    current_step_index += 1
                    current_step = pitch_steps[current_step_index]
                    cl.user_session.set("current_step_index", current_step_index)
                    cl.user_session.set("current_step", current_step)

                    # Save session to database (don't block on failure)
                    try:
                        # Update total interactions and completed steps
                        await save_session_to_db(
                            student_id,
                            current_step_index,
                            total_interactions=step_interactions.get(current_step_key, 0)
                        )
                    except Exception as e:
                        logging.error(f"Error saving session after step completion: {e}")

                    # Inform the student they've moved to the next step
                    await cl.Message(content=f"✅ **Great job!** Moving to the next step: **{current_step}**").send()
                elif current_step_index == total_steps - 1:
                    # They've completed all steps
                    await cl.Message(content="🎉 **Congratulations!** You've completed all steps of your elevator pitch. You can now upload your final pitch using `/upload` or continue refining it.").send()

                    # Save session to database (don't block on failure)
                    try:
                        # Update total interactions and completed steps
                        await save_session_to_db(
                            student_id,
                            current_step_index,
                            total_interactions=step_interactions.get(current_step_key, 0)
                        )
                    except Exception as e:
                        logging.error(f"Error saving session after completion: {e}")

        # Update memory
        agent_memory = cl.user_session.get(f"{selected_agent}_memory", ChatMessageHistory())
        agent_memory.add_user_message(message.content)
        agent_memory.add_ai_message(ai_text)
        cl.user_session.set(f"{selected_agent}_memory", agent_memory)

        # Increment interaction count in database
        try:
            await increment_interactions(student_id)
        except Exception as e:
            logging.error(f"Error incrementing interactions: {e}")

    except Exception as e:
        error_msg = str(e)
        logging.error(f"❌ Error in message processing: {error_msg}")

        # Provide a more user-friendly error message
        if "missing variables" in error_msg.lower():
            await cl.Message(content="⚠️ **System Error**\n\n"
                                    "There was an issue with processing your message. This is likely due to a configuration problem.\n\n"
                                    "Please try refreshing the page and starting a new session.").send()
        elif "openai" in error_msg.lower():
            await cl.Message(content="⚠️ **AI Service Error**\n\n"
                                    "There was an issue connecting to the AI service. Please try again in a moment.").send()
        else:
            await cl.Message(content=f"An error occurred while processing your message. Please try again or refresh the page if the issue persists.").send()

        # Log detailed error for debugging
        logging.error(f"Detailed error: {error_msg}")

async def process_file(file: cl.File):
    pitch_text = extract_text_from_file(file)
    student_id = cl.user_session.get("student_id")
    current_step = cl.user_session.get("current_step", "Final Pitch")

    # Check if student ID exists
    if not student_id:
        await cl.Message(content="⚠️ **Session Error**\n\n"
                                "Your session appears to have expired or you haven't logged in.\n"
                                "Please refresh the page and enter your Student ID again.").send()
        return

    if not pitch_text:
        await cl.Message(content="❌ Couldn't extract text. Please upload a valid `.pdf` or `.docx`.").send()
        return

    try:
        response = await agents["eval"].ainvoke({"pitch": pitch_text})
        feedback = response.content

        match = re.search(r"[Ss]core[:\s]+(\d{1,2})\s*/\s*10", feedback)
        score = int(match.group(1)) if match else None

        # Save the evaluation to the database
        save_result = await save_pitch_evaluation(
            student_id=student_id,
            step_name=current_step,
            score=score,
            feedback=feedback
        )

        if not save_result:
            logging.warning(f"Failed to save pitch evaluation for student {student_id}")

        # Create evaluation message with metadata
        eval_msg = cl.Message(content=f"✅ Evaluation Complete:\n\n{feedback}")

        # Add metadata to the evaluation message
        eval_msg.metadata = {
            "student_id": student_id,
            "agent": "eval",
            "evaluation_score": score,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Send the evaluation message
        await eval_msg.send()

    except Exception as e:
        error_msg = str(e)
        logging.error(f"❌ Evaluation Error: {error_msg}")

        # Provide more specific error messages based on the type of error
        if "connect" in error_msg.lower() or "database" in error_msg.lower():
            await cl.Message(content="⚠️ **Database Connection Error**\n\n"
                                   "There was an issue connecting to the database to store your pitch evaluation.\n\n"
                                   f"Your pitch was successfully evaluated, but we couldn't save it to the database.\n\n"
                                   f"Error details: {error_msg}\n\n"
                                   f"Please take a screenshot of this message and your Student ID: #{student_id}").send()
        elif "openai" in error_msg.lower():
            await cl.Message(content="⚠️ **AI Service Error**\n\n"
                                   "There was an issue connecting to the AI service for evaluation.\n"
                                   "Please try again in a moment.").send()
        else:
            await cl.Message(content="⚠️ Error during pitch evaluation. Please try again.\n\n"
                                   f"Error details: {error_msg}").send()

@cl.on_stop
async def stop_execution():
    """Clear user session on stop."""
    # Get student ID before clearing session
    student_id = cl.user_session.get("student_id", "unknown")
    cl.user_session.clear()
    await cl.Message(f"Session stopped. Your progress is saved! Remember your Student ID: #{student_id}").send()

