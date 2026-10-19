import { Link, NavLink, Route, Routes, useLocation } from 'react-router'

import { ErrorBoundary } from './components/ErrorBoundary'

import { DashboardPage } from './pages/DashboardPage'
import { EditPatientPage } from './pages/EditPatientPage'
import { NewPatientPage } from './pages/NewPatientPage'
import { PatientDetailPage } from './pages/PatientDetailPage'
import { PatientListPage } from './pages/PatientListPage'

export default function App() {
  const location = useLocation()
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="app-title">
          Healthcare Dashboard
        </Link>
        <span className="app-note">Synthetic data only</span>
        <nav className="header-nav" aria-label="Quick actions">
          <Link to="/patients/new" className="button button-primary">
            New patient
          </Link>
        </nav>
      </header>
      <nav className="sidebar" aria-label="Main">
        <ul>
          <li>
            <NavLink to="/" end>
              Dashboard
            </NavLink>
          </li>
          <li>
            {/* Stays highlighted on a patient's chart and edit pages too. */}
            <NavLink to="/patients">Patients</NavLink>
          </li>
        </ul>
      </nav>
      <main className="app-main">
        <ErrorBoundary key={location.pathname}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/patients" element={<PatientListPage />} />
            <Route path="/patients/new" element={<NewPatientPage />} />
            <Route path="/patients/:patientId" element={<PatientDetailPage />} />
            <Route path="/patients/:patientId/edit" element={<EditPatientPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
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
