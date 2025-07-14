# 🧠 AI Tutor: A Multi-Agent Educational Assistant

This project is a multi-agent AI tutoring system built with **Chainlit**, **LangChain**, and **OpenAI's GPT models**. It simulates an interactive tutor that guides students through a structured learning journey, providing mentorship, peer collaboration, progress tracking, and evaluation feedback.

Originally designed for a real-world classroom experiment at NOVA IMS, this project is now released publicly for learning, research, and further development.

---

## ✨ Features

- 🔁 **Agent Switching:** Interact with 4 agents:
  - **Mentor** – explains and guides
  - **Peer** – collaborates and challenges
  - **Progress** – tracks learning steps
  - **Evaluator** – scores and gives structured feedback
- 📎 **File Uploads:** Supports PDF and DOCX uploads
- 📊 **Database Logging:** Tracks user sessions and pitch evaluations with PostgreSQL
- 📄 **Pitch Evaluation Mode:** Evaluate written outputs using a rubric
- 🧠 **OpenAI GPT-4o or Custom Model Support:** Run locally or via API

---

## 🛠️ Tech Stack

- [Chainlit](https://docs.chainlit.io/) — Chat UI for LLM agents
- [LangChain](https://www.langchain.com/) — Agent framework and memory handling
- [PostgreSQL](https://www.postgresql.org/) — Persistent database for session storage
- [OpenAI API](https://platform.openai.com/docs) — GPT-4o or GPT-3.5 Turbo
- Optional: [Ollama](https://ollama.com/) — For local LLM inference (e.g., Mistral, LLaMA 3)

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-tutor-public.git
cd ai-tutor-public
```

### 2. Set Up Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Required: OpenAI API Key
OPENAI_API_KEY=your-openai-api-key-here

# Required: PostgreSQL Database URL
DATABASE_URL=postgresql://username:password@localhost:5432/ai_tutor

# Optional: Application Port (default: 8000)
PORT=8000
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Database

Create a PostgreSQL database and run the following SQL to create the required tables:

```sql
-- Create student sessions table
CREATE TABLE IF NOT EXISTS student_sessions (
    student_id VARCHAR(20) PRIMARY KEY,
    current_step_index INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    session_start_time TIMESTAMP DEFAULT NOW(),
    total_interactions INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    last_message_content TEXT
);

-- Create pitch evaluations table
CREATE TABLE IF NOT EXISTS pitch_evaluations (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(20),
    pitch_content TEXT,
    evaluation_score INTEGER,
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 5. Run the Application

```bash
chainlit run my_agent_bot.py --port 8000
```

The application will be available at `http://localhost:8000`

---

## 🐳 Docker Deployment

### Build and Run with Docker

```bash
# Build the image
docker build -t ai-tutor .

# Run with environment variables
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your-key-here \
  -e DATABASE_URL=your-db-url-here \
  ai-tutor
```

---

## ☁️ Railway.app Deployment

This application is optimized for deployment on [Railway.app](https://railway.app):

1. **Connect your GitHub repository** to Railway
2. **Add a PostgreSQL database** service
3. **Set environment variables:**
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `DATABASE_URL`: Automatically provided by Railway PostgreSQL
   - `PORT`: Automatically provided by Railway
4. **Deploy** - Railway will automatically build and deploy your application

---

## 📖 Usage Guide

### Basic Commands

- `/mentor` - Switch to Mentor Agent for guidance
- `/peer` - Switch to Peer Agent for collaboration
- `/progress` - Check your current progress
- `/eval` - Switch to Evaluator Agent for feedback
- `/next` - Move to the next step
- `/upload` - Submit your final pitch for evaluation

### The 5-Step Process

1. **Problem Identification** - Define the problem your idea solves
2. **Solution Overview** - Explain your solution approach
3. **Value Proposition** - Highlight unique benefits
4. **Target Audience** - Identify who benefits most
5. **Call to Action** - Create a compelling next step

---

## 🔧 Configuration

### Chainlit Configuration

The application uses `chainlit.toml` for configuration. Key settings:

- **File uploads**: PDF and DOCX support enabled
- **Session timeout**: 1 hour for active sessions
- **Database**: PostgreSQL integration enabled

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `PORT` | No | Application port (default: 8000) |

---

## 🧪 Development

### Local Development Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up local PostgreSQL:**
   ```bash
   # Using Docker
   docker run --name ai-tutor-db -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres
   ```

3. **Run in development mode:**
   ```bash
   chainlit run my_agent_bot.py --watch
   ```

### Testing

The application includes basic error handling and logging. Monitor logs for debugging:

```bash
# View application logs
tail -f chainlit.log
```

---

## 📊 Data Collection

The application automatically tracks:

- **Student sessions**: Progress through the 5 steps
- **Interaction counts**: Number of exchanges per step
- **Pitch evaluations**: Final scores and feedback
- **Session timing**: Duration and completion rates

All data is stored in PostgreSQL for analysis.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built for educational research at NOVA IMS
- Powered by OpenAI's GPT models
- UI framework by Chainlit
- Agent orchestration by LangChain

---

## 📞 Support

For questions or issues:

1. Check the [Issues](https://github.com/YOUR_USERNAME/ai-tutor-public/issues) page
2. Create a new issue with detailed information
3. Include logs and environment details

---

**Happy Learning! 🎓**
