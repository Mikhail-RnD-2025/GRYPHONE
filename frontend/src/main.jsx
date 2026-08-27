// ============================================================
//  GRYPHONE — точка входа фронтенда
//  ------------------------------------------------------------
//  Загружает и запускает приложение, монтируя его в корневой
//  элемент на странице.
// ============================================================
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'

// Находим корневой элемент и создаём точку монтирования.
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
