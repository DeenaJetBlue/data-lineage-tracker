import './LineageFlow.css'

function LineageFlow({ data }) {
  const getStatusColor = (status) => {
    if (!status) return '#d1d5db'
    const lower = status.toLowerCase()
    if (lower.includes('available') || lower.includes('success') || lower.includes('succeeded')) {
      return '#10b981'
    }
    if (lower.includes('error') || lower.includes('failed')) {
      return '#ef4444'
    }
    return '#f59e0b'
  }

  const getStatusIcon = (status) => {
    if (!status) return '○'
    const lower = status.toLowerCase()
    if (lower.includes('available') || lower.includes('success') || lower.includes('succeeded')) {
      return '✓'
    }
    if (lower.includes('error') || lower.includes('failed')) {
      return '✕'
    }
    return '⟳'
  }

  const layers = [
    {
      name: 'ADLS',
      subtitle: 'Data Lake',
      icon: '🔷',
      node: data.adls
    },
    {
      name: 'ADF',
      subtitle: 'Azure Data Factory',
      icon: '🔶',
      node: data.adf
    },
    {
      name: 'DBT STG',
      subtitle: 'Staging Layer',
      icon: '🔹',
      node: data.dbt_stage
    },
    {
      name: 'DBT STAR',
      subtitle: 'Star Layer',
      icon: '⭐',
      node: data.dbt_star
    }
  ]

  return (
    <div className="lineage-flow-container">
      <div className="flow-diagram">
        {layers.map((layer, index) => (
          <div key={layer.name} className="flow-item">
            <div
              className="flow-node"
              style={{
                borderColor: getStatusColor(layer.node?.status),
                backgroundColor:
                  getStatusColor(layer.node?.status) === '#10b981'
                    ? '#ecfdf5'
                    : getStatusColor(layer.node?.status) === '#ef4444'
                    ? '#fef2f2'
                    : getStatusColor(layer.node?.status) === '#f59e0b'
                    ? '#fffbeb'
                    : '#f3f4f6'
              }}
            >
              <div className="node-icon">{layer.icon}</div>
              <div className="node-header">{layer.name}</div>
              <div className="node-subtitle">{layer.subtitle}</div>
              <div
                className="status-indicator"
                style={{ color: getStatusColor(layer.node?.status) }}
                title={layer.node?.status}
              >
                {getStatusIcon(layer.node?.status)}
              </div>
            </div>

            {index < layers.length - 1 && (
              <div className="flow-arrow">→</div>
            )}
          </div>
        ))}
      </div>

      <div className="flow-legend">
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#10b981' }}></span>
          <span>Success</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#f59e0b' }}></span>
          <span>Pending</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#ef4444' }}></span>
          <span>Error</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#d1d5db' }}></span>
          <span>Unknown</span>
        </div>
      </div>
    </div>
  )
}

export default LineageFlow
