import { Link, Navigate, Route, Routes } from 'react-router'

import { EditPatientPage } from './pages/EditPatientPage'
import { NewPatientPage } from './pages/NewPatientPage'
import { PatientDetailPage } from './pages/PatientDetailPage'
import { PatientListPage } from './pages/PatientListPage'

export default function App() {
  return (
    <>
      <header className="app-header">
        <Link to="/patients" className="app-title">
          Healthcare Dashboard
        </Link>
        <span className="app-note">Synthetic data only</span>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/patients" replace />} />
          <Route path="/patients" element={<PatientListPage />} />
          <Route path="/patients/new" element={<NewPatientPage />} />
          <Route path="/patients/:patientId" element={<PatientDetailPage />} />
          <Route path="/patients/:patientId/edit" element={<EditPatientPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  )
}

function NotFound() {
  return (
    <section>
      <h1>Page not found</h1>
      <p>
        <Link to="/patients">Go to the patient list</Link>
      </p>
    </section>
  )
}
