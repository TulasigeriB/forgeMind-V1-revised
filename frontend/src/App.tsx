import React from 'react'
import { Routes, Route } from 'react-router-dom'

const Dashboard = () => (
  <div className="p-8">
    <h1 className="text-3xl font-bold text-slate-800">ForgeMind Dashboard</h1>
    <p className="text-slate-600 mt-2">Welcome to the manufacturing intelligence platform.</p>
    <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="p-4 bg-white rounded-lg shadow border border-slate-200">
        <h3 className="font-semibold">Active Projects</h3>
        <p className="text-2xl font-bold">0</p>
      </div>
      <div className="p-4 bg-white rounded-lg shadow border border-slate-200">
        <h3 className="font-semibold">Pending RFQs</h3>
        <p className="text-2xl font-bold">0</p>
      </div>
      <div className="p-4 bg-white rounded-lg shadow border border-slate-200">
        <h3 className="font-semibold">Quotes Sent</h3>
        <p className="text-2xl font-bold">0</p>
      </div>
    </div>
  </div>
)

function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-brand-dark text-white p-4 flex justify-between items-center">
        <div className="text-xl font-bold tracking-tight">FORGEMIND</div>
        <nav className="space-x-4 text-sm font-medium">
          <a href="#" className="hover:text-blue-400">Projects</a>
          <a href="#" className="hover:text-blue-400">Customers</a>
          <a href="#" className="hover:text-blue-400">Settings</a>
        </nav>
      </header>
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
