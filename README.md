# Safe-Growth Lead Researcher

An AI-powered lead research agent that takes a LinkedIn URL or company name, researches the target, finds recent news, and drafts personalized outreach emails. Built with production-grade features including rate limiting, error handling, security guardrails, and performance optimization.

## 🚀 Features

- **🔍 Intelligent Research**: Scrapes LinkedIn profiles and searches for company news and industry trends
- **📧 Personalized Emails**: Generates customized outreach emails based on research findings
- **🛡️ Security Guardrails**: Detects and blocks prompt injection attempts
- **⚡ Multi-Level Rate Limiting**:
  - Global token governor with RPM/TPM tracking
  - Per-user rate limiting (5 req/min, 20 req/hour) for public deployments
  - Sliding window algorithm for accurate tracking
- **🔄 Error Handling**: Exponential backoff with automatic fallback to secondary sources
- **📊 Real-time Metrics**: Live dashboard showing performance and rate limit status
- **👋 Welcome Overlay**: Interactive onboarding with prompt starters
- **🎯 Streaming Output**: Token-by-token email generation with TTFT tracking
- **🔗 LangSmith Integration**: Full execution tracing and monitoring

## 🏗️ Architecture

Built with:
- **LangGraph**: State management and agent orchestration
- **Google Gemini 1.5 Flash**: Primary LLM (cost-effective, fast)
- **Tavily Search API**: Primary search provider
- **DuckDuckGo**: Fallback search provider
- **FastAPI**: Backend API server
- **Streamlit**: Interactive UI with real-time metrics

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

## 📋 Prerequisites

- Python 3.11+
- Google Gemini API key
- Tavily Search API key (optional, falls back to DuckDuckGo)
- LangSmith API key (optional, for tracing)

## 🛠️ Installation

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/safe-growth-researcher.git
cd safe-growth-researcher
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

5. **Run the application**

**Streamlit UI (Recommended):**
```bash
# Set PYTHONPATH and run
export PYTHONPATH=$PWD  # On Windows: set PYTHONPATH=%CD%
python -m streamlit run src/ui/app.py
```

Or use the launcher script:
```bash
python run_ui.py
```

**FastAPI Backend:**
```bash
# Set PYTHONPATH and run
export PYTHONPATH=$PWD  # On Windows: set PYTHONPATH=%CD%
python -m uvicorn src.api.main:app --reload
```

Or use the launcher script:
```bash
python run_api.py
```

### Docker Deployment

1. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

2. **Start services**
```bash
docker-compose up -d
```

3. **Access the application**
- Streamlit UI: http://localhost:8501
- FastAPI Docs: http://localhost:8000/docs

### 🌐 Public Deployment

When deploying to a public URL (Streamlit Cloud, Heroku, Railway, etc.):

**✅ Built-in Protection:**
- **Per-User Rate Limiting**: Automatically limits each user to 5 requests/minute and 20 requests/hour
- **Session Tracking**: Uses session IDs (Streamlit) or IP addresses (API) to identify users
- **Welcome Overlay**: Educates users about rate limits and proper usage
- **Security Guardrails**: Blocks malicious inputs before they reach the LLM

**📝 Deployment Checklist:**
1. Set environment variables in your hosting platform
2. Ensure `GOOGLE_API_KEY` and `TAVILY_API_KEY` are configured
3. Monitor usage via the metrics dashboard
4. Consider adjusting rate limits in `src/core/user_rate_limiter.py` based on your API quotas
5. Review CORS settings in `src/api/main.py` for production

**🔧 Customizing Rate Limits:**
Edit `src/core/user_rate_limiter.py`:
```python
user_rate_limiter = UserRateLimiter(
    requests_per_minute=5,   # Adjust as needed
    requests_per_hour=20     # Adjust as needed
)
```

## 📖 Usage

### Streamlit UI

1. Open http://localhost:8501
2. **Welcome Screen**: On first visit, you'll see:
   - Overview of what the agent does
   - Prompt starters to try (Google, OpenAI, LinkedIn profiles, etc.)
   - Rate limit information (5 req/min, 20 req/hour per user)
3. Enter a LinkedIn URL or company name (or use a prompt starter)
4. Click "Start Research"
5. View real-time metrics in the sidebar including your personal usage
6. Get personalized email draft
7. **Rate Limiting**: If you exceed limits, wait for the displayed time before trying again

### API Endpoints

**Research Lead:**
```bash
curl -X POST "http://localhost:8000/research" \
  -H "Content-Type: application/json" \
  -d '{"input": "https://linkedin.com/in/john-doe"}'
```

**Rate Limiting:**
- **Per-User Limits** (for public deployments):
  - 5 requests per minute per user
  - 20 requests per hour per user
  - Tracked by IP address (API) or session ID (Streamlit)
- **Global Limits**:
  - Each research submission reserves an estimated token budget: `max(250, min(1000, len(input) * 4))`
  - Respects Gemini API RPM/TPM limits
- **When Blocked**:
  - Streamlit shows user-friendly wait-time message
  - FastAPI returns `HTTP 429 Too Many Requests` with retry information

**Get Metrics:**
```bash
curl "http://localhost:8000/metrics"
```

**Validate Input:**
```bash
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d '{"input": "test input"}'
```

## 🧪 Testing

### Security Testing

Use the "Try to Break Me" section in the UI to test security guardrails:
- Prompt injection attempts
- Jailbreak patterns
- Malicious inputs

### Simulate Failures

Enable "Simulate Tool Failure" toggle to test error handling and fallback mechanisms.

## 📊 Metrics Dashboard

The sidebar displays real-time metrics:
- **Global Metrics**:
  - **RPM**: Requests per minute (current/max)
  - **TPM**: Tokens per minute (current/max)
  - **Total Requests/Tokens**: Cumulative statistics
  - **Requests Blocked**: Number of submissions blocked by rate limiting
- **Your Usage** (per-user):
  - Requests this minute (out of 5)
  - Requests this hour (out of 20)
- **Performance**:
  - **TTFT**: Time to first token
  - **Total Time**: Complete execution time

## 🔒 Security Features

- **Input Validation**: Pre-LLM security layer
- **Prompt Injection Detection**: Regex + pattern matching
- **Multi-Level Rate Limiting**:
  - Per-user limits prevent individual abuse (5/min, 20/hour)
  - Global limits protect API quotas (RPM/TPM)
  - Prevents API credit exhaustion in public deployments
- **Input Sanitization**: Removes harmful content
- **Threat Classification**: Low/Medium/High severity levels

## 🎯 Performance Optimization

- **Parallel Tool Calling**: Concurrent research operations
- **Streaming Architecture**: Real-time output generation
- **Caching**: Reduces redundant API calls
- **Exponential Backoff**: Smart retry logic

## 📁 Project Structure

```
safe-growth-researcher/
├── src/
│   ├── agent/          # LangGraph workflow
│   ├── tools/          # LinkedIn scraper, search tools
│   ├── core/           # Rate limiter, retry handler
│   ├── security/       # Guardrails, validation
│   ├── ui/             # Streamlit application
│   └── api/            # FastAPI backend
├── tests/              # Unit and integration tests
├── requirements.txt    # Python dependencies
├── docker-compose.yml  # Docker orchestration
├── ARCHITECTURE.md     # Detailed architecture
└── README.md          # This file
```

## 🔧 Configuration

Edit `.env` file to configure:

```env
# API Keys
GOOGLE_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
LANGCHAIN_API_KEY=your_key_here

# Rate Limits
GEMINI_RPM=15
GEMINI_TPM=1000000

# Features
ENABLE_GUARDRAILS=true
ENABLE_CACHING=true
ENABLE_TRACING=true
```

## 📈 Rate Limits (Tier 1)

**Google Gemini 1.5 Flash:**
- RPM: 15 requests/minute
- TPM: 1,000,000 tokens/minute
- TPD: 1,500 requests/day

**Tavily Search API:**
- Free Tier: 1,000 searches/month

## 🐛 Troubleshooting

**Import Errors:**
```bash
pip install -r requirements.txt --upgrade
```

**API Key Issues:**
- Verify keys in `.env` file
- Check API key validity
- Ensure proper environment variable loading

**Rate Limit Errors:**
- Monitor the metrics dashboard, especially RPM, TPM, and blocked requests
- Research submissions are checked before execution in both the Streamlit UI and FastAPI `/research` endpoint
- Input submissions reserve an estimated token budget using `max(250, min(1000, len(input) * 4))`
- Adjust rate limits in `.env`
- Wait for the rate limit window to reset before retrying

**LinkedIn Scraping Issues:**
- ⚠️ LinkedIn actively blocks automated scraping
- The scraper is included for demonstration purposes
- For production use, consider:
  - Using LinkedIn's official API
  - Providing company name instead of LinkedIn URL
  - The system will gracefully continue without LinkedIn data
- The workflow will still generate emails using search results

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- LangChain/LangGraph for agent framework
- Google for Gemini API
- Tavily for search API
- Streamlit for UI framework

## 📞 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/safe-growth-researcher/issues)
- Documentation: [ARCHITECTURE.md](ARCHITECTURE.md)

---

**Built with ❤️ for Safe-Growth**