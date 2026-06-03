# PDF Chatbot Frontend

The frontend project is contained in `frontend/`. It is a React + Vite single page application for authentication, notebook selection, PDF upload, document filtering, and RAG chat. All screens are served from one frontend domain/port and are selected by path-based routing.

## Directory Structure

```text
frontend/
|-- config/
|   `-- nginx/
|-- public/
|-- src/
|   |-- app/
|   |   `-- AppContext.jsx
|   |-- components/
|   |   |-- AppHeader.jsx
|   |   |-- AuthScreen.jsx
|   |   |-- ChatPanel.jsx
|   |   |-- DocumentsPanel.jsx
|   |   |-- NotebookPanel.jsx
|   |   `-- StatusSidebar.jsx
|   |-- layouts/
|   |   |-- AdminLayout.jsx
|   |   |-- AuthLayout.jsx
|   |   `-- DashboardLayout.jsx
|   |-- pages/
|   |   |-- admin/
|   |   |-- auth/
|   |   |-- dashboard/
|   |   `-- system/
|   |-- routes/
|   |   |-- adminRoutes.jsx
|   |   |-- authRoutes.jsx
|   |   |-- dashboardRoutes.jsx
|   |   |-- guards.jsx
|   |   `-- index.jsx
|   |-- api.js
|   |-- App.jsx
|   |-- formatters.js
|   |-- main.jsx
|   |-- usePdfChatbotApp.js
|   `-- styles.css
|-- Dockerfile
|-- package.json
`-- vite.config.js
```

## Routing

- `src/App.jsx` mounts `AppProvider` and the centralized React Router instance.
- `src/routes/index.jsx` composes public, protected, and admin route groups.
- `src/routes/authRoutes.jsx` contains `/login`, `/register`, `/forgot-password`, and `/reset-password`.
- `src/routes/dashboardRoutes.jsx` contains `/dashboard`, `/chat`, `/chat/:id`, `/documents`, `/documents/:id`, `/history`, `/analytics`, `/settings`, and `/profile`.
- `src/routes/adminRoutes.jsx` contains `/admin` and `/admin/users/:userId`.
- `src/routes/guards.jsx` contains the protected route, public-only route, and admin guard.
- `config/nginx/default.conf` serves `index.html` as the fallback for direct access and page reloads on nested frontend routes.

## Organization Notes

- `src/app/AppContext.jsx` owns the shared application state from `usePdfChatbotApp`.
- `src/components/` contains the UI panels and shared header used by that screen.
- `src/usePdfChatbotApp.js` contains state and workflow logic for auth, notebooks, PDF upload, and chat.
- `src/api.js` contains API config, fetch helpers, and local session persistence.
- `src/formatters.js` contains small display formatting helpers.

## Running Locally

```bash
cd frontend
npm ci
npm run dev
```

The Vite dev server proxies `/api` to the backend based on `VITE_API_PROXY_TARGET` or `VITE_API_BASE_URL`.
