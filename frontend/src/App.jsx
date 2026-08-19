import { useState, useEffect } from 'react'
import TableSearch from './components/TableSearch'
import LineageViewer from './components/LineageViewer'
import './App.css'

function App() {
  const [selectedTable, setSelectedTable] = useState(null)

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>📊 Data Lineage Tracker</h1>
          <p>Track data flow: ADLS → ADF → Snowflake Raw → DBT STG → DBT Star</p>
        </div>
      </header>
      <main className="app-main">
        {selectedTable ? (
          <LineageViewer
            tableName={selectedTable}
            onBack={() => setSelectedTable(null)}
          />
        ) : (
          <TableSearch onSelectTable={setSelectedTable} />
        )}
      </main>
    </div>
  )
}

export default App
