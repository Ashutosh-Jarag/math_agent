# 🧮 Math Routing Agent

A full-stack **AI Math Assistant** that provides step-by-step solutions to math problems using advanced AI and vector search capabilities.

## 🌟 Overview

This application combines **Google Gemini API**, **Qdrant Vector Database**, **FastAPI**, and **React** to create an intelligent math tutoring system that:
- Retrieves relevant solutions from a knowledge base
- Generates step-by-step explanations
- Falls back to web search when needed
- Learns from user feedback

---

## 🚀 Key Features

✅ **Step-by-step explanations** for calculus, algebra, geometry, and more  
✅ **Vector-based knowledge retrieval** using Qdrant  
✅ **AI-powered reasoning** via Google Gemini  
✅ **Web search fallback** for questions outside the knowledge base  
✅ **User feedback system** with retraining capability  
✅ **Modern React UI** with Tailwind CSS styling  
✅ **Input/output guardrails** for math-specific queries  

---

## 🏗️ Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   React     │ ─HTTP─> │   FastAPI    │ ─────> │   Gemini    │
│  Frontend   │         │   Backend    │         │     API     │
└─────────────┘         └──────────────┘         └─────────────┘
                               │                          
                               │                          
                        ┌──────▼───────┐         
                        │    Qdrant    │         
                        │ Vector Store │         
                        └──────────────┘         
```

---

## 📁 Project Structure

```
math_agent/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── utils.py                # Helper functions (Gemini, Qdrant)
│   ├── scripts/
│   │   ├── ingest_kb.py        # Ingest CSV into Qdrant
│   │   ├── retrain_kb.py       # Retrain from feedback
│   │   └── search_kb.py        # Test knowledge base search
│   ├── data/
│   │   └── math_kb.csv         # Knowledge base dataset
│   ├── feedback_log.csv        # User feedback (auto-generated)
│   ├── requirements.txt        # Python dependencies
│   └── .env                    # Environment variables
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main React component
│   │   ├── main.jsx            # React entry point
│   │   ├── api.js              # API service layer
│   │   ├── styles.css          # Tailwind imports
│   │   └── components/
│   │       ├── AskForm.jsx     # Question input form
│   │       ├── AnswerCard.jsx  # Answer display
│   │       └── FeedbackForm.jsx # Feedback submission
│   ├── package.json            # Node dependencies
│   ├── vite.config.js          # Vite configuration
│   ├── tailwind.config.js      # Tailwind CSS config
│   └── postcss.config.js       # PostCSS config
│
└── README.md                   # This file
```

---

## 🛠️ Installation & Setup

### Prerequisites

- **Python 3.10+**
- **Node.js 16+** and npm
- **Docker** (for Qdrant)
- **Google API Key** for Gemini ([Get it here](https://makersuite.google.com/app/apikey))

---

## 🔧 Backend Setup

### 1. Create Python Virtual Environment

```bash
cd backend
python3 -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `backend/.env` file:

```env
GOOGLE_API_KEY=your_google_api_key_here
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=math_kb
GEMINI_EMBED_MODEL=embedding-001
GEMINI_GEN_MODEL=gemini-2.5-flash
KB_THRESHOLD=0.78
KB_TOPK=3
SERPER_API_KEY=your_serper_key_here  # Optional: for web search
```

### 4. Start Qdrant Vector Database

```bash
docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

**Expected output:**
```
Server started on 0.0.0.0:6333
```

### 5. Ingest Knowledge Base

```bash
cd backend
source myenv/bin/activate
python3 scripts/ingest_kb.py
```

**Expected output:**
```
✅ Done ingesting KB into Qdrant.
```

### 6. Start Backend Server

```bash
uvicorn main:app --reload
```

**Access the API at:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 💻 Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Tailwind CSS

Ensure these files exist:

**tailwind.config.js:**
```javascript
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: { extend: {} },
  plugins: [],
}
```

**postcss.config.js:**
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

**src/styles.css:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 3. Start Development Server

```bash
npm run dev
```

**Access the app at:** [http://localhost:5173](http://localhost:5173)

---

## 🎯 Usage

### Asking a Question

1. Open the frontend at `http://localhost:5173`
2. Enter a math question (e.g., "Integrate 2x dx")
3. Select explanation level: **Quick**, **Detailed**, or **Advanced**
4. Click "Get Answer"

### Example API Request

**Endpoint:** `POST /ask`

```json
{
  "question": "Differentiate x^3 + 2x^2 - 5x",
  "explain_level": "detailed",
  "user_id": "student_001"
}
```

**Response:**

```json
{
  "steps": [
    "1. Write f(x) = x³ + 2x² - 5x",
    "2. Apply power rule: d(xⁿ)/dx = n·xⁿ⁻¹",
    "3. Derivative of x³ is 3x²",
    "4. Derivative of 2x² is 4x",
    "5. Derivative of -5x is -5",
    "6. Combine: f'(x) = 3x² + 4x - 5"
  ],
  "final_answer": "f'(x) = 3x² + 4x - 5",
  "sources": ["1"],
  "confidence": 0.95
}
```

---

## 🔄 Feedback & Retraining

### Submit Feedback

Users can rate answers and provide corrections through the feedback form. Feedback is automatically saved to `backend/feedback_log.csv`.

### Retrain Knowledge Base

To incorporate valuable feedback into the knowledge base:

```bash
cd backend
source myenv/bin/activate
python3 scripts/retrain_kb.py
```

This script:
1. Reads high-quality feedback (rating ≥ 4)
2. Adds new entries to Qdrant
3. Updates the knowledge base

---

## 🧪 Testing

### Test Knowledge Base Search

```bash
cd backend
python3 scripts/search_kb.py
```

Enter a query to see matching results from Qdrant.

### API Testing

Use the Swagger UI at [http://localhost:8000/docs](http://localhost:8000/docs) to test:
- `/ask` - Ask math questions
- `/feedback` - Submit feedback
- `/health` - Check server status

---

## 🚀 Quick Start After Reboot

Whenever you restart your machine:

```bash
# 1. Start Qdrant
docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant

# 2. Start Backend (in new terminal)
cd backend
source myenv/bin/activate
uvicorn main:app --reload

# 3. Start Frontend (in new terminal)
cd frontend
npm run dev
```

---

## 📊 Knowledge Base Format

The knowledge base (`data/math_kb.csv`) follows this structure:

```csv
id,question,final_answer,steps,tags
1,"Differentiate f(x)=x^3","f'(x)=3x^2","1. Apply power rule...","calculus,derivative"
```

**Fields:**
- `id` - Unique identifier
- `question` - Math problem
- `final_answer` - Final result
- `steps` - Step-by-step solution
- `tags` - Category tags (comma-separated)

---

## 🔒 Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API key | Required |
| `QDRANT_URL` | Qdrant server URL | `http://localhost:6333` |
| `COLLECTION_NAME` | Vector collection name | `math_kb` |
| `GEMINI_EMBED_MODEL` | Embedding model | `embedding-001` |
| `GEMINI_GEN_MODEL` | Generation model | `gemini-2.5-flash` |
| `KB_THRESHOLD` | Similarity threshold | `0.78` |
| `KB_TOPK` | Top results to retrieve | `3` |
| `SERPER_API_KEY` | Web search API key | Optional |

---

## 🛡️ Features

### Input Guardrails
- Validates math-related queries
- Rejects harmful or irrelevant content
- Ensures appropriate question format

### Output Guardrails
- Filters AI-generated responses
- Ensures step-by-step clarity
- Validates mathematical correctness

### Knowledge Base Retrieval
- Vector similarity search via Qdrant
- Configurable similarity threshold
- Multiple result aggregation

### Web Search Fallback
- Activates when KB confidence is low
- Uses Serper API for search
- Integrates results into answer generation

---

## 🐛 Troubleshooting

### Qdrant Connection Error
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Restart Qdrant
docker restart <container_id>
```

### Port Already in Use
```bash
# Backend (port 8000)
lsof -ti:8000 | xargs kill -9

# Frontend (port 5173)
lsof -ti:5173 | xargs kill -9
```

### Missing Dependencies
```bash
# Backend
pip install -r requirements.txt

# Frontend
npm install
```

---

## 📚 Tech Stack

**Backend:**
- FastAPI - Modern Python web framework
- Google Gemini - AI reasoning and embeddings
- Qdrant - Vector similarity search
- Pydantic - Data validation

**Frontend:**
- React 18 - UI framework
- Vite - Build tool
- Tailwind CSS - Styling
- Axios - HTTP client

**Infrastructure:**
- Docker - Containerization
- Uvicorn - ASGI server

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the **MIT License** - see the LICENSE file for details.

---

## 👨‍💻 Author

**Ashutosh Jarag**  
B.Tech in Computer Science @ Shivaji University, Kolhapur  
Data Science & AI Enthusiast | Power BI | Python | FastAPI | React  

---

## 🙏 Acknowledgments

- Google Gemini API for AI capabilities
- Qdrant for vector search infrastructure
- FastAPI community for excellent documentation
- React and Tailwind CSS teams for frontend tools

---

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Contact: jaragashutosh11@gmail.com

---

**⭐ Star this repository if you find it helpful!**