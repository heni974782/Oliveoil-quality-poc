import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { getToken } from './shared/auth'
import Navbar from './shared/components/Navbar'
import LoginPage from './features/auth/LoginPage'
import ConsignmentsPage from './features/consignments/ConsignmentsPage'
import ConsignmentDetailPage from './features/consignments/ConsignmentDetailPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div className="min-h-screen bg-slate-900 text-slate-100">
                <Navbar />
                <Routes>
                  <Route path="/" element={<ConsignmentsPage />} />
                  <Route path="/consignments/:id" element={<ConsignmentDetailPage />} />
                </Routes>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
