import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import POMBrowser from '../components/POMBrowser/POMBrowser'
import POMCatalogue from '../components/POMBrowser/POMCatalogue'

// `activeTab` value is the id (Browser/Catalogue) → kept; label resolved from poms.tab_* at render.
const TABS = [['Browser', 'poms.tab_browser'], ['Catalogue', 'poms.tab_catalogue']]

export default function POMs() {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState('Browser')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 100px)' }}>
      <div style={{ marginBottom: '0.8rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>{t('poms.title')}</h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>
          {t('poms.subtitle')}
        </p>
      </div>

      {/* Tira de pestanyes — Browser (assign, validat a B3-ter) i Catalogue (placeholder, B5). */}
      <div style={{ display: 'flex', gap: 8, marginBottom: '0.8rem' }}>
        {TABS.map(([tab, labelKey]) => (
          <button key={tab} type="button"
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '6px 16px', borderRadius: 6, border: 'none',
              background: activeTab === tab ? 'var(--gold)' : 'var(--bg-muted)',
              color: activeTab === tab ? 'var(--white)' : 'var(--text-muted)',
              cursor: 'pointer', fontSize: 13,
              fontWeight: activeTab === tab ? 500 : 400,
            }}>
            {t(labelKey)}
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
