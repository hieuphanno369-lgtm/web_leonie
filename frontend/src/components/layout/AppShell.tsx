import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function AppShell() {
  return (
    <div className="dark min-h-screen bg-primary flex">
      <Sidebar />
      <main className="flex-1 ml-56 overflow-y-auto min-h-screen">
        <Outlet />
      </main>
    </div>
  )
}
