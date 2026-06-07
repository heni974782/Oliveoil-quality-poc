import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Navbar from './shared/components/Navbar'
import ConsignmentsPage from './features/consignments/ConsignmentsPage'
import ConsignmentDetailPage from './features/consignments/ConsignmentDetailPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-900 text-slate-100">
        <Navbar />
        <Routes>
          <Route path="/" element={<ConsignmentsPage />} />
          <Route path="/consignments/:id" element={<ConsignmentDetailPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
