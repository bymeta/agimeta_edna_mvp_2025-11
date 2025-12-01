'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { fetchScanStatus, ScanStatus } from '@/lib/api'

export default function ScansPage() {
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadScanStatus()
    // Refresh every 30 seconds
    const interval = setInterval(loadScanStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  async function loadScanStatus() {
    setLoading(true)
    setError(null)
    try {
      const status = await fetchScanStatus()
      setScanStatus(status)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load scan status')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'running':
        return 'bg-blue-100 text-blue-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <Link href="/" className="text-xl font-semibold text-gray-900">
                  Enterprise DNA
                </Link>
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
                  className="border-blue-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
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
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Scanner Status</h1>
            <button
              onClick={loadScanStatus}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Refresh
            </button>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{error}</div>
            </div>
          )}

          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading scan status...</p>
            </div>
          ) : scanStatus ? (
            <div className="bg-white shadow overflow-hidden sm:rounded-lg">
              <div className="px-4 py-5 sm:p-6">
                <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Status</dt>
                    <dd className="mt-1">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(scanStatus.status)}`}>
                        {scanStatus.status.charAt(0).toUpperCase() + scanStatus.status.slice(1)}
                      </span>
                    </dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Last Run</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {scanStatus.last_run
                        ? new Date(scanStatus.last_run).toLocaleString()
                        : 'Never'}
                    </dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Tables Scanned</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {scanStatus.tables_scanned > 0
                        ? scanStatus.tables_scanned
                        : 'N/A'}
                    </dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Candidates Created</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {scanStatus.candidates_created}
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          ) : null}

          <div className="mt-6 bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">About Scanner</h2>
              <p className="text-sm text-gray-600">
                The scanner service profiles PostgreSQL tables and creates object candidates.
                Run the scanner manually using: <code className="bg-gray-100 px-2 py-1 rounded">docker compose run --rm scanner</code>
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

