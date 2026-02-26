from backend.llm.ollama_client import ask_coder, parse_json_response


FRONTEND_PROMPT = """Generate React frontend files for this app.

App: {prompt}
Pages needed: {pages}
API endpoints: {api_spec}

Return ONLY valid JSON with actual working code:
{{
  "files": [
    {{
      "path": "frontend/src/pages/Login.jsx",
      "content": "import {{useState}} from 'react'\\nexport default function Login() {{\\n  return <div>Login Page</div>\\n}}"
    }},
    {{
      "path": "frontend/src/pages/Dashboard.jsx", 
      "content": "import {{useState,useEffect}} from 'react'\\nexport default function Dashboard() {{\\n  return <div>Dashboard</div>\\n}}"
    }},
    {{
      "path": "frontend/src/App.jsx",
      "content": "import {{BrowserRouter as Router,Route,Routes}} from 'react-router-dom'\\nimport Login from './pages/Login'\\nimport Dashboard from './pages/Dashboard'\\nexport default function App(){{return(<Router><Routes><Route path='/' element={{<Login/>}}/><Route path='/dashboard' element={{<Dashboard/>}}/></Routes></Router>)}}"
    }},
    {{
      "path": "frontend/package.json",
      "content": "{{\\\"name\\\":\\\"app\\\",\\\"version\\\":\\\"1.0.0\\\",\\\"scripts\\\":{{\\\"dev\\\":\\\"vite\\\"}},\\\"dependencies\\\":{{\\\"react\\\":\\\"^18.2.0\\\",\\\"react-dom\\\":\\\"^18.2.0\\\",\\\"react-router-dom\\\":\\\"^6.8.0\\\",\\\"axios\\\":\\\"^1.3.0\\\"}},\\\"devDependencies\\\":{{\\\"@vitejs/plugin-react\\\":\\\"^4.2.0\\\",\\\"vite\\\":\\\"^5.0.0\\\",\\\"tailwindcss\\\":\\\"^3.4.0\\\",\\\"autoprefixer\\\":\\\"^10.4.16\\\",\\\"postcss\\\":\\\"^8.4.32\\\"}}}}"
    }},
    {{
      "path": "frontend/index.html",
      "content": "<!DOCTYPE html><html><head><meta charset='UTF-8'/><title>App</title></head><body><div id='root'></div><script type='module' src='/src/main.jsx'></script></body></html>"
    }},
    {{
      "path": "frontend/src/main.jsx",
      "content": "import React from 'react'\\nimport ReactDOM from 'react-dom/client'\\nimport App from './App.jsx'\\nimport './index.css'\\nReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>)"
    }},
    {{
      "path": "frontend/src/index.css",
      "content": "@tailwind base;\\n@tailwind components;\\n@tailwind utilities;"
    }},
    {{
      "path": "frontend/vite.config.js",
      "content": "import {{defineConfig}} from 'vite'\\nimport react from '@vitejs/plugin-react'\\nexport default defineConfig({{plugins:[react()],server:{{port:3000,host:true}}}})"
    }},
    {{
      "path": "frontend/postcss.config.js",
      "content": "module.exports={{plugins:{{tailwindcss:{{}},autoprefixer:{{}}}}}}"
    }},
    {{
      "path": "frontend/tailwind.config.js",
      "content": "module.exports={{content:['./index.html','./src/**/*.{{js,jsx}}'],theme:{{extend:{{}}}},plugins:[]}}"
    }}
  ],
  "pages": {pages_list},
  "summary": "frontend generated"
}}

Generate REAL working React code for each page. Use Tailwind for styling. Make it look good.
"""


async def generate_frontend(plan: dict, backend_result: dict, websocket=None) -> dict:
    async def emit(event: str, message: str):
        if websocket:
            await websocket.send_json({"event": event, "message": message})

    await emit("stage", "Generating frontend...")

    prompt = plan["prompt"]
    api_spec = backend_result.get("api_spec", {"endpoints": []})
    
    # Format endpoints
    endpoints = api_spec.get("endpoints", [])
    api_str = "\n".join([f"{e.get('method','GET')} {e.get('path','/')}" for e in endpoints[:8]])
    if not api_str:
        api_str = "GET /api/items, POST /api/items, DELETE /api/items/:id"

    # Get pages from plan
    answers = plan["interview"]["main"].get("answers", {})
    pages = answers.get("pages", ["Login", "Register", "Dashboard"])
    if isinstance(pages, str):
        pages = [p.strip() for p in pages.split(",")]
    
    pages_str = ", ".join(pages)
    pages_list = str(pages).replace("'", '"')

    raw = await ask_coder(FRONTEND_PROMPT.format(
        prompt=prompt,
        pages=pages_str,
        api_spec=api_str,
        pages_list=pages_list
    ))

    try:
        result = parse_json_response(raw)
        files = result.get("files", [])
        await emit("stage", f"Frontend generated — {len(files)} files")
        return {"files": files, "pages": pages}
    except Exception as e:
        await emit("warning", f"Frontend generation failed: {str(e)}, using defaults")
        # Return base files that always work
        return {
            "files": _get_base_frontend(prompt, pages),
            "pages": pages
        }


def _get_base_frontend(prompt: str, pages: list) -> list:
    """Fallback — always returns working base frontend files."""
    
    page_imports = "\n".join([f"import {p} from './pages/{p}'" for p in pages])
    page_routes = "\n".join([f"<Route path='/{p.lower()}' element={{<{p}/>}}/>" for p in pages])
    first_page = pages[0] if pages else "Home"

    return [
        {
            "path": "frontend/package.json",
            "content": '{"name":"app","version":"1.0.0","scripts":{"dev":"vite"},"dependencies":{"react":"^18.2.0","react-dom":"^18.2.0","react-router-dom":"^6.8.0","axios":"^1.3.0"},"devDependencies":{"@vitejs/plugin-react":"^4.2.0","vite":"^5.0.0","tailwindcss":"^3.4.0","autoprefixer":"^10.4.16","postcss":"^8.4.32"}}'
        },
        {
            "path": "frontend/index.html",
            "content": "<!DOCTYPE html><html><head><meta charset='UTF-8'/><title>App</title></head><body><div id='root'></div><script type='module' src='/src/main.jsx'></script></body></html>"
        },
        {
            "path": "frontend/vite.config.js",
            "content": "import {defineConfig} from 'vite'\nimport react from '@vitejs/plugin-react'\nexport default defineConfig({plugins:[react()],server:{port:3000,host:true}})"
        },
        {
            "path": "frontend/postcss.config.js",
            "content": "module.exports={plugins:{tailwindcss:{},autoprefixer:{}}}"
        },
        {
            "path": "frontend/tailwind.config.js",
            "content": "module.exports={content:['./index.html','./src/**/*.{js,jsx}'],theme:{extend:{}},plugins:[]}"
        },
        {
            "path": "frontend/src/main.jsx",
            "content": "import React from 'react'\nimport ReactDOM from 'react-dom/client'\nimport App from './App.jsx'\nimport './index.css'\nReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>)"
        },
        {
            "path": "frontend/src/index.css",
            "content": "@tailwind base;\n@tailwind components;\n@tailwind utilities;"
        },
        {
            "path": "frontend/src/App.jsx",
            "content": f"import {{BrowserRouter as Router,Route,Routes}} from 'react-router-dom'\n{page_imports}\nexport default function App(){{return(<Router><Routes><Route path='/' element={{<{first_page}/>}}/>{page_routes}</Routes></Router>)}}"
        },
        *[_generate_page(p) for p in pages]
    ]


def _generate_page(page_name: str) -> dict:
    """Generate a basic working page component."""
    return {
        "path": f"frontend/src/pages/{page_name}.jsx",
        "content": f"""import {{ useState, useEffect }} from 'react'
import axios from 'axios'

export default function {page_name}() {{
  const [data, setData] = useState([])
  const [input, setInput] = useState('')

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">{page_name}</h1>
        <div className="bg-gray-800 rounded-lg p-6">
          <input
            value={{input}}
            onChange={{e => setInput(e.target.value)}}
            placeholder="Enter something..."
            className="w-full bg-gray-700 px-4 py-2 rounded mb-4"
          />
          <button
            onClick={{() => setData([...data, input])}}
            className="bg-green-500 hover:bg-green-600 px-4 py-2 rounded"
          >
            Submit
          </button>
          <div className="mt-4 flex flex-col gap-2">
            {{data.map((item, i) => (
              <div key={{i}} className="bg-gray-700 px-4 py-2 rounded">{{item}}</div>
            ))}}
          </div>
        </div>
      </div>
    </div>
  )
}}"""
    }
