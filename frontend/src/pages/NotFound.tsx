import { Link, useLocation } from 'react-router-dom'
import { Compass, ArrowLeft } from 'lucide-react'

export default function NotFound() {
  const { pathname } = useLocation()
  return (
    <div className="flex-1 flex items-center justify-center min-h-screen bg-gray-950 p-6">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-home/10 border border-home/20 flex items-center justify-center">
          <Compass size={28} className="text-home" />
        </div>
        <h1 className="text-5xl font-bold text-white mb-2">404</h1>
        <p className="text-gray-300 text-sm mb-1">
          Trang này chưa tồn tại hoặc đang được phát triển.
        </p>
        <p className="text-gray-600 text-xs mb-6 font-mono break-all">{pathname}</p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm
                     bg-home/10 border border-home/30 text-home hover:bg-home/20 transition-all"
        >
          <ArrowLeft size={15} /> Về Dashboard
        </Link>
      </div>
    </div>
  )
}
