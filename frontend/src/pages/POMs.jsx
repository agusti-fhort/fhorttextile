import { useState } from 'react'
import POMBrowser from '../components/POMBrowser/POMBrowser'
import POMCatalogue from '../components/POMBrowser/POMCatalogue'

const TABS = ['Browser', 'Catalogue']

export default function POMs() {
  const [activeTab, setActiveTab] = useState('Browser')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 100px)' }}>
      <div style={{ marginBottom: '0.8rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>POM Systems</h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>
          Catàleg de Points of Measure per tipus de prenda
        </p>
      </div>

      {/* Tira de pestanyes — Browser (assign, validat a B3-ter) i Catalogue (placeholder, B5). */}
      <div style={{ display: 'flex', gap: 8, marginBottom: '0.8rem' }}>
        {TABS.map(tab => (
          <button key={tab} type="button"
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '6px 16px', borderRadius: 6, border: 'none',
              background: activeTab === tab ? 'var(--gold)' : 'var(--color-background-secondary, #f5f0ea)',
              color: activeTab === tab ? '#fff' : 'var(--color-text-secondary, #868685)',
              cursor: 'pointer', fontSize: 13,
              fontWeight: activeTab === tab ? 500 : 400,
            }}>
            {tab}
          </button>
        ))}
      </div>

      <div style={{
        flex: 1, overflow: 'hidden',
        background: 'var(--white)',
        border: '0.5px solid #e4e4e2',
        borderRadius: 12,
      }}>
        {activeTab === 'Browser' && <POMBrowser mode="assign" />}
        {activeTab === 'Catalogue' && <POMCatalogue />}
      </div>
    </div>
  )
}
