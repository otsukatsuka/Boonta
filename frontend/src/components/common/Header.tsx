import { Link } from 'react-router-dom';

export function Header() {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <Link to="/" className="flex items-center">
              <span className="text-2xl font-bold text-primary-600">Boonta</span>
              <span className="ml-2 text-sm text-gray-500">競馬予想AI</span>
            </Link>
          </div>

          <nav className="flex space-x-8">
            <Link
              to="/"
              className="text-gray-600 hover:text-primary-600 px-3 py-2 text-sm font-medium"
            >
              ダッシュボード
            </Link>
            <Link
              to="/races"
              className="text-gray-600 hover:text-primary-600 px-3 py-2 text-sm font-medium"
            >
              レース一覧
            </Link>
            <Link
              to="/data-input"
              className="text-gray-600 hover:text-primary-600 px-3 py-2 text-sm font-medium"
            >
              データ入力
            </Link>
            <Link
              to="/model"
              className="text-gray-600 hover:text-primary-600 px-3 py-2 text-sm font-medium"
            >
              モデル状態
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
