import Link from 'next/link'

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-semibold text-gray-900">Enterprise DNA</h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link
                  href="/objects"
                  className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Objects
                </Link>
                <Link
                  href="/scans"
                  className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Scans
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Enterprise DNA Cockpit</h2>
            <p className="text-gray-600 mb-8">Manage golden objects, view scans, and monitor your data platform</p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Link
                href="/objects"
                className="block p-6 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
              >
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Objects</h3>
                <p className="text-gray-600">Browse and manage golden business objects</p>
              </Link>
              <Link
                href="/scans"
                className="block p-6 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
              >
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Scans</h3>
                <p className="text-gray-600">View scanner run status and results</p>
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

