import { useState, useEffect } from 'react'
import axios from 'axios'
import './TableSearch.css'

function TableSearch({ onSelectTable }) {
  const [tables, setTables] = useState([])
  const [filteredTables, setFilteredTables] = useState([])
  const [searchInput, setSearchInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchTables()
  }, [])

  const fetchTables = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await axios.get('/api/tables')
      if (response.data.success) {
        setTables(response.data.data.tables)
        setFilteredTables(response.data.data.tables)
      }
    } catch (err) {
      setError('Failed to fetch tables. Make sure the backend is running.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (value) => {
    setSearchInput(value)
    if (value.trim() === '') {
      setFilteredTables(tables)
    } else {
      const filtered = tables.filter(table =>
        table.toLowerCase().includes(value.toLowerCase())
      )
      setFilteredTables(filtered)
    }
  }

  const handleTableClick = (table) => {
    onSelectTable(table)
  }

  return (
    <div className="table-search">
      <div className="search-container">
        <h2>Select a Table to View Lineage</h2>

        <div className="search-box">
          <input
            type="text"
            placeholder="🔍 Search tables..."
            value={searchInput}
            onChange={(e) => handleSearch(e.target.value)}
            className="search-input"
            disabled={loading}
          />
        </div>

        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        {loading ? (
          <div className="loading">Loading tables...</div>
        ) : filteredTables.length > 0 ? (
          <div className="tables-grid">
            {filteredTables.map(table => (
              <div
                key={table}
                className="table-card"
                onClick={() => handleTableClick(table)}
              >
                <div className="table-icon">📋</div>
                <div className="table-info">
                  <div className="table-name">{table}</div>
                  <div className="table-action">View Lineage →</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="no-results">
            ❌ No tables found matching "{searchInput}"
          </div>
        )}

        {!searchInput && tables.length > 0 && (
          <div className="info-box">
            <p>💡 Click on any table to see its complete data lineage flow</p>
            <p>📊 The lineage shows the journey of your data through each system</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default TableSearch
