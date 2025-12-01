'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { fetchObjects, fetchObjectTypes, BusinessObject } from '@/lib/api'

export default function ObjectsPage() {
  const [objects, setObjects] = useState<BusinessObject[]>([])
  const [objectTypes, setObjectTypes] = useState<string[]>([])
  const [selectedType, setSelectedType] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const limit = 50

  useEffect(() => {
    loadObjectTypes()
  }, [])

  useEffect(() => {
    loadObjects()
  }, [selectedType, offset])

  async function loadObjectTypes() {
    try {
      const types = await fetchObjectTypes()
      setObjectTypes(types)
    } catch (err) {
      console.error('Failed to load object types:', err)
    }
  }

  async function loadObjects() {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchObjects(selectedType || undefined, limit, offset)
      setObjects(response.objects)
      setTotal(response.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load objects')
    } finally {
      setLoading(false)
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
                  className="border-blue-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
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
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Business Objects</h1>
            
            <div className="flex items-center gap-4 mb-4">
              <label htmlFor="type-filter" className="text-sm font-medium text-gray-700">
                Filter by Type:
              </label>
              <select
                id="type-filter"
                value={selectedType}
                onChange={(e) => {
                  setSelectedType(e.target.value)
                  setOffset(0)
                }}
                className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              >
                <option value="">All Types</option>
                {objectTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
              <span className="text-sm text-gray-600">
                {total} total object{total !== 1 ? 's' : ''}
              </span>
            </div>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{error}</div>
            </div>
          )}

          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading objects...</p>
            </div>
          ) : objects.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-600">No objects found</p>
            </div>
          ) : (
            <>
              <div className="bg-white shadow overflow-hidden sm:rounded-md">
                <ul className="divide-y divide-gray-200">
                  {objects.map((obj) => (
                    <li key={obj.golden_id}>
                      <Link
                        href={`/objects/${obj.golden_id}`}
                        className="block hover:bg-gray-50 transition-colors"
                      >
                        <div className="px-4 py-4 sm:px-6">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center">
                              <p className="text-sm font-medium text-blue-600 truncate">
                                {obj.golden_id.substring(0, 16)}...
                              </p>
                              <span className="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                {obj.object_type}
                              </span>
                            </div>
                            <div className="ml-2 flex-shrink-0 flex">
                              <p className="text-sm text-gray-500">
                                {obj.source_system}:{obj.source_id}
                              </p>
                            </div>
                          </div>
                          <div className="mt-2 sm:flex sm:justify-between">
                            <div className="sm:flex">
                              <p className="flex items-center text-sm text-gray-500">
                                Created: {new Date(obj.created_at).toLocaleString()}
                              </p>
                            </div>
                          </div>
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mt-4 flex items-center justify-between">
                <button
                  onClick={() => setOffset(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-700">
                  Showing {offset + 1} to {Math.min(offset + limit, total)} of {total}
                </span>
                <button
                  onClick={() => setOffset(offset + limit)}
                  disabled={offset + limit >= total}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  )
}

