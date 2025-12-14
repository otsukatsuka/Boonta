import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/common';
import { Dashboard, RaceList, RaceDetail, DataInput, ModelStatus } from './pages';

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/races" element={<RaceList />} />
            <Route path="/races/:raceId" element={<RaceDetail />} />
            <Route path="/data-input" element={<DataInput />} />
            <Route path="/model" element={<ModelStatus />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
