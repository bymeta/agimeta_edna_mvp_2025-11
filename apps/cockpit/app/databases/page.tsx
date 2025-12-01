'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { 
  fetchSourceDatabases, 
  createSourceDatabase, 
  updateSourceDatabase, 
  deleteSourceDatabase,
  checkSourceDatabaseConnection,
  SourceDatabase,
  SourceDatabaseConnectionCheckResult,
} from '@/lib/api'

export default function DatabasesPage() {
  const [databases, setDatabases] = useState<SourceDatabase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingDb, setEditingDb] = useState<SourceDatabase | null>(null)
  const [formData, setFormData] = useState({
    source_db_id: '',
    source_db_name: '',
    description: '',
    host: '',
    port: 5432,
    database_name: '',
    username: '',
    password_encrypted: '',
    schemas: [] as string[],
    table_blacklist: [] as string[],
    active: true,
  })
  const [schemaInput, setSchemaInput] = useState('')
  const [blacklistInput, setBlacklistInput] = useState('')
  const [connectionStatus, setConnectionStatus] = useState<Record<string, SourceDatabaseConnectionCheckResult>>({})
  const [checkingId, setCheckingId] = useState<string | null>(null)

  useEffect(() => {
    loadDatabases()
  }, [])

  async function loadDatabases() {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchSourceDatabases(false)
      setDatabases(response.databases)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load databases')
    } finally {
      setLoading(false)
    }
  }

  function handleEdit(db: SourceDatabase) {
    setEditingDb(db)
    setFormData({
      source_db_id: db.source_db_id,
      source_db_name: db.source_db_name,
      description: db.description || '',
      host: db.host,
      port: db.port,
      database_name: db.database_name,
      username: db.username,
      password_encrypted: '', // Don't pre-fill password
      schemas: db.schemas || [],
      table_blacklist: db.table_blacklist || [],
      active: db.active,
    })
    setSchemaInput((db.schemas || []).join(', '))
    setBlacklistInput((db.table_blacklist || []).join(', '))
    setShowForm(true)
  }

  function handleDelete(db: SourceDatabase) {
    if (!confirm(`Are you sure you want to delete "${db.source_db_name}"?`)) {
      return
    }

    deleteSourceDatabase(db.source_db_id)
      .then(() => {
        loadDatabases()
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to delete database')
      })
  }

  async function handleCheckConnection(db: SourceDatabase) {
    setCheckingId(db.source_db_id)
    setError(null)

    try {
      const result = await checkSourceDatabaseConnection(db.source_db_id)
      setConnectionStatus((prev) => ({
        ...prev,
        [db.source_db_id]: result,
      }))
    } catch (err) {
      setConnectionStatus((prev) => ({
        ...prev,
        [db.source_db_id]: {
          status: 'failed',
          error: err instanceof Error ? err.message : 'Connection check failed',
        },
      }))
    } finally {
      setCheckingId(null)
    }
  }

  function handleNew() {
    setEditingDb(null)
    setFormData({
      source_db_id: '',
      source_db_name: '',
      description: '',
      host: '',
      port: 5432,
      database_name: '',
      username: '',
      password_encrypted: '',
      schemas: [],
      table_blacklist: [],
      active: true,
    })
    setSchemaInput('')
    setBlacklistInput('')
    setShowForm(true)
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    // Parse schemas and blacklist from comma-separated strings
    const schemas = schemaInput.split(',').map(s => s.trim()).filter(s => s)
    const blacklist = blacklistInput.split(',').map(s => s.trim()).filter(s => s)

    const dbData = {
      ...formData,
      schemas,
      table_blacklist: blacklist,
    }

    const promise = editingDb
      ? updateSourceDatabase(editingDb.source_db_id, dbData)
      : createSourceDatabase(dbData)

    promise
      .then(() => {
        setShowForm(false)
        loadDatabases()
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to save database')
      })
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
                  className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Scans
                </Link>
                <Link
                  href="/databases"
                  className="border-blue-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                >
                  Databases
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="mb-6 flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">Source Databases</h1>
            <button
              onClick={handleNew}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
            >
              Add Database
            </button>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-800">{error}</div>
            </div>
          )}

          {showForm && (
            <div className="mb-6 bg-white shadow rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4">
                {editingDb ? 'Edit Database' : 'New Database'}
              </h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Database ID *</label>
                    <input
                      type="text"
                      required
                      value={formData.source_db_id}
                      onChange={(e) => setFormData({ ...formData, source_db_id: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      disabled={!!editingDb}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Database Name *</label>
                    <input
                      type="text"
                      required
                      value={formData.source_db_name}
                      onChange={(e) => setFormData({ ...formData, source_db_name: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    rows={2}
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Host *</label>
                    <input
                      type="text"
                      required
                      value={formData.host}
                      onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Port *</label>
                    <input
                      type="number"
                      required
                      value={formData.port}
                      onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) || 5432 })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Database Name *</label>
                    <input
                      type="text"
                      required
                      value={formData.database_name}
                      onChange={(e) => setFormData({ ...formData, database_name: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Username *</label>
                    <input
                      type="text"
                      required
                      value={formData.username}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Password *</label>
                    <input
                      type="password"
                      required={!editingDb}
                      value={formData.password_encrypted}
                      onChange={(e) => setFormData({ ...formData, password_encrypted: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      placeholder={editingDb ? "Leave empty to keep current password" : ""}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Schemas (comma-separated, empty = all)</label>
                  <input
                    type="text"
                    value={schemaInput}
                    onChange={(e) => setSchemaInput(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    placeholder="public, sales, crm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Table Blacklist (comma-separated patterns with %)</label>
                  <input
                    type="text"
                    value={blacklistInput}
                    onChange={(e) => setBlacklistInput(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    placeholder="temp_%, log_%, edna_%"
                  />
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.active}
                    onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label className="ml-2 block text-sm text-gray-900">Active</label>
                </div>

                <div className="flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
                  >
                    {editingDb ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading databases...</p>
            </div>
          ) : databases.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-lg shadow">
              <p className="text-gray-600 mb-4">No source databases configured</p>
              <button
                onClick={handleNew}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
              >
                Add First Database
              </button>
            </div>
          ) : (
            <div className="bg-white shadow overflow-hidden sm:rounded-md">
              <ul className="divide-y divide-gray-200">
                {databases.map((db) => (
                  <li key={db.source_db_id} className="px-4 py-4 sm:px-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{db.source_db_name}</p>
                          <p className="text-sm text-gray-500">
                            {db.host}:{db.port}/{db.database_name}
                          </p>
                          {db.description && (
                            <p className="text-sm text-gray-500 mt-1">{db.description}</p>
                          )}
                        </div>
                        <div className="ml-4">
                          {db.active ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                              Inactive
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {db.last_scan_at && (
                          <div className="text-xs text-gray-500">
                            Last scan: {new Date(db.last_scan_at).toLocaleString()}
                            {db.last_scan_status && (
                              <span className={`ml-2 ${db.last_scan_status === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                                ({db.last_scan_status})
                              </span>
                            )}
                          </div>
                        )}
                        <button
                          onClick={() => handleCheckConnection(db)}
                          disabled={checkingId === db.source_db_id}
                          className="px-3 py-1 text-sm text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {checkingId === db.source_db_id ? 'Checking...' : 'Check Connection'}
                        </button>
                        <button
                          onClick={() => handleEdit(db)}
                          className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(db)}
                          className="px-3 py-1 text-sm text-red-600 hover:text-red-800"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                    <div className="mt-2 text-xs text-gray-500">
                      {db.schemas && db.schemas.length > 0 && (
                        <span>Schemas: {db.schemas.join(', ')}</span>
                      )}
                      {db.table_blacklist && db.table_blacklist.length > 0 && (
                        <span className="ml-4">Blacklist: {db.table_blacklist.join(', ')}</span>
                      )}
                      {connectionStatus[db.source_db_id] && (
                        <span className="ml-4">
                          Connection:{' '}
                          {connectionStatus[db.source_db_id].status === 'success' ? (
                            <span className="text-green-600">
                              OK
                              {typeof connectionStatus[db.source_db_id].latency_ms === 'number' &&
                                ` (${connectionStatus[db.source_db_id].latency_ms} ms)`}
                            </span>
                          ) : (
                            <span className="text-red-600">
                              Failed
                              {connectionStatus[db.source_db_id].error && `: ${connectionStatus[db.source_db_id].error}`}
                            </span>
                          )}
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

