import { useState, useEffect } from 'react'
import axios from 'axios'
import LineageFlow from './LineageFlow'
import './LineageViewer.css'

function LineageViewer({ tableName, onBack }) {
  const [lineage, setLineage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchLineage()
  }, [tableName])

  const fetchLineage = async () => {
    try {
      setLoading(true)
      setError(null)
      console.log(`📖 Fetching lineage for table: ${tableName}`)
      const response = await axios.get(`/api/lineage/${tableName}`)
      console.log('✅ Lineage data received:', response.data)

      if (response.data.success) {
        setLineage(response.data.data)
        console.log('✅ Lineage loaded successfully')
      } else {
        setError(response.data.error || 'Failed to fetch lineage')
        console.error('❌ API returned error:', response.data.error)
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to fetch lineage data'
      setError(errorMsg)
      console.error('❌ Error fetching lineage:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="lineage-viewer">
        <button className="btn-back" onClick={onBack}>← Back</button>
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading lineage data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="lineage-viewer">
        <button className="btn-back" onClick={onBack}>← Back</button>
        <div className="error-container">
          <h3>⚠️ Error</h3>
          <p>{error}</p>
          <button className="btn-retry" onClick={fetchLineage}>Retry</button>
        </div>
      </div>
    )
  }

  if (!lineage) {
    return (
      <div className="lineage-viewer">
        <button className="btn-back" onClick={onBack}>← Back</button>
        <div className="error-container">
          <p>No lineage data available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="lineage-viewer">
      <button className="btn-back" onClick={onBack}>← Back to Tables</button>

      <div className="lineage-header">
        <h2>📊 Data Lineage for <span className="table-name">{tableName}</span></h2>
      </div>

      <LineageFlow data={lineage} />

      <div className="lineage-details">
        <div className="detail-column">
          <h3>🔷 ADLS (Data Lake)</h3>
          <div className="detail-card">
            {lineage.adls ? (
              <>
                <div className="detail-row">
                  <span className="label">Path:</span>
                  <span className="value">{lineage.adls.path}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Status:</span>
                  <span className={`status status-${lineage.adls.status}`}>
                    {lineage.adls.status}
                  </span>
                </div>
                {lineage.adls.last_modified && (
                  <div className="detail-row">
                    <span className="label">Last Modified:</span>
                    <span className="value">
                      {new Date(lineage.adls.last_modified).toLocaleString()}
                    </span>
                  </div>
                )}
                {lineage.adls.error && (
                  <div className="detail-row error">
                    <span className="label">Error:</span>
                    <span className="value">{lineage.adls.error}</span>
                  </div>
                )}
              </>
            ) : (
              <p className="no-data">No data available</p>
            )}
          </div>
        </div>

        <div className="detail-column">
          <h3>🔶 Azure Data Factory</h3>
          <div className="detail-card">
            {lineage.adf ? (
              <>
                <div className="detail-row">
                  <span className="label">Pipeline:</span>
                  <span className="value">{lineage.adf.pipeline_name}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Status:</span>
                  <span className={`status status-${lineage.adf.status}`}>
                    {lineage.adf.status}
                  </span>
                </div>
                {lineage.adf.last_run && (
                  <div className="detail-row">
                    <span className="label">Last Run:</span>
                    <span className="value">
                      {new Date(lineage.adf.last_run).toLocaleString()}
                    </span>
                  </div>
                )}
                {lineage.adf.run_id && (
                  <div className="detail-row">
                    <span className="label">Run ID:</span>
                    <span className="value">{lineage.adf.run_id}</span>
                  </div>
                )}
                {lineage.adf.error && (
                  <div className="detail-row error">
                    <span className="label">Error:</span>
                    <span className="value">{lineage.adf.error}</span>
                  </div>
                )}
              </>
            ) : (
              <p className="no-data">No data available</p>
            )}
          </div>
        </div>

        <div className="detail-column">
          <h3>🔹 DBT Staging Layer</h3>
          <div className="detail-card">
            {lineage.dbt_stage ? (
              <>
                <div className="detail-row">
                  <span className="label">Job Name:</span>
                  <span className="value">{lineage.dbt_stage.job_name}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Latest Run Status:</span>
                  <span className={`status status-${lineage.dbt_stage.status}`}>
                    {lineage.dbt_stage.status}
                  </span>
                </div>
                {lineage.dbt_stage.job_status && (
                  <div className="detail-row">
                    <span className="label">Job Status:</span>
                    <span className={`status status-${lineage.dbt_stage.job_status}`}>
                      {lineage.dbt_stage.job_status}
                    </span>
                  </div>
                )}
                {lineage.dbt_stage.last_run && (
                  <div className="detail-row">
                    <span className="label">Last Run Time:</span>
                    <span className="value">
                      {new Date(lineage.dbt_stage.last_run).toLocaleString()}
                    </span>
                  </div>
                )}
                {lineage.dbt_stage.run_id && (
                  <div className="detail-row">
                    <span className="label">Run ID:</span>
                    <span className="value">{lineage.dbt_stage.run_id}</span>
                  </div>
                )}
                {lineage.dbt_stage.job_id && (
                  <div className="detail-row">
                    <span className="label">Job ID:</span>
                    <span className="value">{lineage.dbt_stage.job_id}</span>
                  </div>
                )}
                {lineage.dbt_stage.error && (
                  <div className="detail-row error">
                    <span className="label">Error:</span>
                    <span className="value">{lineage.dbt_stage.error}</span>
                  </div>
                )}
              </>
            ) : (
              <p className="no-data">No data available</p>
            )}
          </div>
        </div>

        <div className="detail-column">
          <h3>⭐ DBT Star Layer</h3>
          <div className="detail-card">
            {lineage.dbt_star ? (
              <>
                <div className="detail-row">
                  <span className="label">Job Name:</span>
                  <span className="value">{lineage.dbt_star.job_name}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Latest Run Status:</span>
                  <span className={`status status-${lineage.dbt_star.status}`}>
                    {lineage.dbt_star.status}
                  </span>
                </div>
                {lineage.dbt_star.job_status && (
                  <div className="detail-row">
                    <span className="label">Job Status:</span>
                    <span className={`status status-${lineage.dbt_star.job_status}`}>
                      {lineage.dbt_star.job_status}
                    </span>
                  </div>
                )}
                {lineage.dbt_star.last_run && (
                  <div className="detail-row">
                    <span className="label">Last Run Time:</span>
                    <span className="value">
                      {new Date(lineage.dbt_star.last_run).toLocaleString()}
                    </span>
                  </div>
                )}
                {lineage.dbt_star.run_id && (
                  <div className="detail-row">
                    <span className="label">Run ID:</span>
                    <span className="value">{lineage.dbt_star.run_id}</span>
                  </div>
                )}
                {lineage.dbt_star.job_id && (
                  <div className="detail-row">
                    <span className="label">Job ID:</span>
                    <span className="value">{lineage.dbt_star.job_id}</span>
                  </div>
                )}
                {lineage.dbt_star.error && (
                  <div className="detail-row error">
                    <span className="label">Error:</span>
                    <span className="value">{lineage.dbt_star.error}</span>
                  </div>
                )}
              </>
            ) : (
              <p className="no-data">No data available</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default LineageViewer
