# Safe-Growth Lead Researcher

An AI-powered lead research agent that takes a LinkedIn URL or company name, researches the target, finds recent news, and drafts personalized outreach emails. Built with production-grade features including rate limiting, error handling, security guardrails, and performance optimization.

## 🚀 Features

- **🔍 Intelligent Research**: Scrapes LinkedIn profiles and searches for company news and industry trends
- **📧 Personalized Emails**: Generates customized outreach emails based on research findings
- **🛡️ Security Guardrails**: Detects and blocks prompt injection attempts
- **⚡ Rate Limiting**: Token governor with RPM/TPM tracking and sliding window algorithm
- **🔄 Error Handling**: Exponential backoff with automatic fallback to secondary sources
- **📊 Real-time Metrics**: Live dashboard showing performance and rate limit status
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

## 📖 Usage

### Streamlit UI

1. Open http://localhost:8501
2. Enter a LinkedIn URL or company name
3. Click "Start Research"
4. View real-time metrics in the sidebar
5. Get personalized email draft

### API Endpoints

**Research Lead:**
```bash
curl -X POST "http://localhost:8000/research" \
  -H "Content-Type: application/json" \
  -d '{"input": "https://linkedin.com/in/john-doe"}'
```

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
- **RPM**: Requests per minute (current/max)
- **TPM**: Tokens per minute (current/max)
- **TTFT**: Time to first token
- **Total Time**: Complete execution time
- **Total Requests/Tokens**: Cumulative statistics

## 🔒 Security Features

- **Input Validation**: Pre-LLM security layer
- **Prompt Injection Detection**: Regex + pattern matching
- **Rate Limiting**: Prevents API abuse
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
- Monitor metrics dashboard
- Adjust rate limits in `.env`
- Wait for rate limit window to reset

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