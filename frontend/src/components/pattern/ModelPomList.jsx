import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import { formatDelta, formatLen, titleLen } from '../../utils/format'

/**
 * POMS DEL MODEL — la LLISTA DE TREBALL del taller (W3).
 *
 * No és el catàleg global de POMs: són les Mesures d'AQUEST model, les que la fitxa ja
 * dona per bones. **Els POMs no es busquen: es col·loquen.** Una fila PENDENT és un botó:
 * clicar-la entra al mode de col·locació D'AQUELL POM, i el canvas guia (punt A → punt B).
 * Cap cercador pel mig — el cercador de catàleg queda com a acció secundària, per al POM
 * que no és a la fitxa.
 *
 * Una fila COL·LOCADA ensenya el que això persegueix: què deia la fitxa, què mesura el
 * patró, i la diferència. La tolerància només pinta l'estat quan n'hi ha: sense tolerància
 * es dona la xifra i no es jutja.
 *
 * NOMENCLATURA (convenció de la casa): el codi de client mana i el nom va a sota, en gris.
 *
 * **El valor de FITXA és la referència, i es pinta com a tal** (QA-TALLER C · T2). Abans era
 * petit i gris —la xifra contra la qual es compara tot, amagada— i el mesurat era el gran.
 * Ara els dos números manen igual, en negre: qui mira la fila compara DUES xifres. Qui jutja
 * és el XIP de tolerància, i el judici és seu i de ningú més: **la xifra no es tenyeix mai**.
 * Un número vermell obliga a endevinar si és vermell perquè està fora o perquè és important;
 * un xip vermell al costat d'un número negre ho diu.
 */
export default function ModelPomList({
  files, poms = [], pomActiu, pomSelId = null, onColocar, onAfegirFora,
  onReobre, onEsborra, onAssenyala, unit = 'CM',
}) {
  const { t, i18n } = useTranslation()
  const [obert, setObert] = useState(null)
  const [menu, setMenu] = useState(null)

  // El POM ancorat sencer, pel seu id. Les files de la fitxa només porten un resum de cada
  // ancoratge (`pattern_pom`, peça, valor, Δ); reobrir-ne un vol la RECEPTA i el mètode, que
  // viuen a la llista d'ancorats. Per això el panell rep les dues coses i les creua aquí.
  const pomPerId = useMemo(() => new Map(poms.map(p => [p.id, p])), [poms])

  // ELS ANCORATS QUE NO SÓN A LA FITXA. La llista de treball recorre les Mesures del model,
  // o sigui que un POM ancorat per la via secundària —el que la fitxa no demana— no hi surt
  // per cap banda. Amb dos panells es veia al de l'altre costat; amb un de sol, fondre'ls
  // sense això l'hauria fet DESAPARÈIXER, que és el pitjor que pot fer una fusió de llistes.
  const forans = useMemo(() => {
    const deLaFitxa = new Set(
      files.flatMap(f => (f.ancoratges || []).map(a => a.pattern_pom)))
    return poms.filter(p => !deLaFitxa.has(p.id))
  }, [files, poms])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {files.length === 0 ? (
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', margin: 0 }}>
          {t('pattern.taller.model_poms_empty')}
        </p>
      ) : files.map(f => (
        <Fila
          key={f.base_measurement} t={t} lang={i18n.language} f={f} unit={unit}
          actiu={pomActiu?.base_measurement === f.base_measurement}
          pomSelId={pomSelId}
          onColocar={() => onColocar(f)}
          obert={obert === f.base_measurement}
          onInfo={() => setObert(o => (o === f.base_measurement ? null : f.base_measurement))}
          onTanca={() => setObert(null)}
          menuObert={menu === f.base_measurement}
          onMenu={() => setMenu(m => (m === f.base_measurement ? null : f.base_measurement))}
          onTancaMenu={() => setMenu(null)}
          pomPerId={pomPerId}
          onReobre={onReobre} onEsborra={onEsborra} onAssenyala={onAssenyala}
        />
      ))}

      {/* Els ancorats que la fitxa no demana. Van al final i amb rètol propi: són feina
          legítima, però no són la llista de treball. */}
      {forans.length > 0 && (
        <>
          <p style={{
            margin: '0.5rem 0 0', fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
          }}>
            {t('pattern.taller.pom_outside_group', { n: forans.length })}
          </p>
          {forans.map(p => (
            <FilaForana
              key={p.id} t={t} p={p} unit={unit}
              sel={pomSelId === p.id}
              menuObert={menu === `f${p.id}`}
              onMenu={() => setMenu(m => (m === `f${p.id}` ? null : `f${p.id}`))}
              onTancaMenu={() => setMenu(null)}
              onReobre={onReobre} onEsborra={onEsborra} onAssenyala={onAssenyala}
            />
          ))}
        </>
      )}

      {/* Via SECUNDÀRIA: el POM que no és a la fitxa. Existeix (algú vol mesurar una cosa
          que la fitxa no demana), però no mana la pantalla: la feina és la llista. */}
      <button
        onClick={onAfegirFora}
        style={{
          marginTop: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.35rem',
          background: 'none', border: '1.5px dashed var(--line)', borderRadius: 4,
          padding: '0.35rem 0.6rem', cursor: 'pointer',
          fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
        }}
      >
        <i className="ti ti-plus" />
        {t('pattern.taller.pom_outside')}
      </button>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * El text d'un camp multilingüe del catàleg, en l'idioma de qui mira.
 *
 * El servidor envia els idiomes en CRU i no en tria cap (i18n-gate: qui té els tres idiomes
 * és la UI). ⚠️ `POMGlobal` NO té descripció en castellà —només `en` i `ca`—, així que un
 * usuari en `es` cau a l'anglès: és la descripció canònica internacional, i val més la que hi
 * ha que un buit.
 */
function enIdioma(camps, lang) {
  if (!camps) return ''
  const codi = (lang || 'ca').slice(0, 2)
  return camps[codi] || camps.en || camps.ca || ''
}

function Fila({
  t, lang, f, actiu, onColocar, unit, obert, onInfo, onTanca,
  menuObert, onMenu, onTancaMenu, pomPerId, pomSelId,
  onReobre, onEsborra, onAssenyala,
}) {
  const colocat = f.ancorat
  // Assenyalar una cota al canvas ha de ressaltar LA SEVA FILA. Sense això el lligam
  // canvas↔llista quedava construït a mitges: la fila forana s'encenia i les de la fitxa
  // —que són la majoria— no deien res.
  const assenyalada = (f.ancoratges || []).some(a => a.pattern_pom === pomSelId)

  // L'estat de la Δ: només es jutja si es POT jutjar. `dins_tolerancia` ve a null quan la
  // fitxa no dona valor (plantilla sense mesura) — llavors hi ha xifra, però no veredicte.
  const estat = f.dins_tolerancia == null ? null : f.dins_tolerancia

  // El nom CANÒNIC en anglès mana la fila: és el que el catàleg internacional en diu, i és
  // el que no canvia entre clients. Si el POM no té global (n'hi ha), es cau al nom del
  // client, que és millor que una fila sense nom.
  const nomCanonic = f.nom?.en || f.nom_client || f.nom_canonic || ''
  const descripcio = enIdioma(f.descripcio, lang)
  const alias = f.alias_client

  return (
    <div
      style={{
        position: 'relative',
        background: (actiu || assenyalada) ? 'var(--sel)' : 'var(--panel)',
        border: `1px solid ${(actiu || assenyalada) ? 'var(--gold)' : 'var(--line)'}`,
        // NORMA §4: tota selecció porta filet d'or de 3px. Quan la fila NO està triada, el
        // filet segueix fent la seva altra feina —dir si el POM ja és col·locat.
        borderLeft: `3px solid ${(actiu || assenyalada) ? 'var(--gold)'
          : colocat ? 'var(--ok)' : 'var(--line)'}`,
        borderRadius: 4,
        display: 'flex', alignItems: 'center',
      }}
    >
      {/* La fila és el botó de col·locar, però la «i» NO hi pot viure a dins: un botó dins
          d'un botó no és HTML vàlid i el clic no arribaria mai. Per això la fila és un
          contenidor i els dos botons són germans. */}
      <button
        onClick={colocat ? undefined : onColocar}
        disabled={colocat}
        aria-pressed={actiu}
        title={colocat ? undefined : t('pattern.taller.pom_place_hint', { codi: f.codi_client })}
        style={{
          textAlign: 'left', flex: 1, minWidth: 0,
          cursor: colocat ? 'default' : 'pointer',
          background: 'none', border: 'none', borderRadius: 4,
          padding: '0.3rem 0.5rem',
          display: 'flex', alignItems: 'center', gap: '0.5rem',
        }}
      >
        <i
          className={`ti ${colocat ? 'ti-circle-check' : actiu ? 'ti-crosshair' : 'ti-circle-dashed'}`}
          style={{ color: colocat ? 'var(--ok)' : actiu ? 'var(--gold)' : 'var(--text-soft)',
                   flexShrink: 0 }}
        />

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            display: 'flex', alignItems: 'baseline', gap: '0.35rem',
            fontSize: 'var(--fs-body)', fontWeight: 600,
          }}>
            <span style={{ fontFamily: 'var(--mono)' }}>{f.codi_client}</span>
            <span style={{
              fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              {nomCanonic}
            </span>
            {/* La nomenclatura de la fletxa al croquis: és com el patronista l'anomena al
                dibuix, i per això va al costat del codi i no amagada al detall. */}
            {f.nom_fitxa && (
              <span style={{
                fontSize: 'var(--fs-caption)', fontWeight: 400, color: 'var(--text-soft)',
                border: '1px solid var(--line)', borderRadius: 8, padding: '0 5px',
                flexShrink: 0,
              }}>
                {f.nom_fitxa}
              </span>
            )}
          </div>

          {/* La descripció canònica en l'idioma de qui mira: què és aquesta mesura, dit una
              vegada i bé. Va gris i petita perquè no competeix amb el nom — s'hi recorre. */}
          {descripcio && (
            <div style={{
              fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {descripcio}
            </div>
          )}

          {/* Com en diu EL CLIENT. Només hi és quan es pot dir sense inventar (un sol àlies):
              el servidor calla si n'hi ha dos, i aquí no se n'hi posa cap de recanvi. */}
          {alias?.description_local && (
            <div style={{
              fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              fontStyle: 'italic',
            }}>
              {t('pattern.taller.pom_client_says', { text: alias.description_local })}
            </div>
          )}

          {colocat && f.peca && (
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>
              {f.peca}
            </div>
          )}
        </div>

        {/* ELS DOS NÚMEROS (T2). Tots dos grans i negres: la fitxa és la referència i el
            mesurat és el que se li compara — pintar-ne un de petit i gris obligava a buscar
            contra què s'estava comparant. El `title` porta els valors COMPLETS: la dada no
            s'arrodoneix mai, només la seva imatge. */}
        <div
          title={[
            f.valor_mesurat_cm != null ? `${t('pattern.taller.value_pattern_t')}: ${titleLen(f.valor_mesurat_cm)}` : null,
            f.valor_fitxa_cm != null ? `${t('pattern.taller.value_sheet_t')}: ${titleLen(f.valor_fitxa_cm)}` : null,
          ].filter(Boolean).join(' · ') || undefined}
          style={{
            textAlign: 'right', fontFamily: 'var(--mono)', flexShrink: 0, lineHeight: 1.35,
            display: 'flex', alignItems: 'center', gap: '0.4rem',
          }}
        >
          <div style={{ textAlign: 'right' }}>
            <div style={{
              display: 'flex', alignItems: 'baseline', justifyContent: 'flex-end',
              gap: '0.35rem',
            }}>
              <span style={{
                color: 'var(--text-main)', fontWeight: 600, fontSize: 'var(--fs-body)',
              }}>
                {f.valor_fitxa_cm != null
                  ? formatLen(f.valor_fitxa_cm, unit)
                  : t('pattern.taller.value_sheet_none')}
              </span>
              {colocat && f.valor_mesurat_cm != null && (
                <>
                  <span style={{ color: 'var(--text-soft)', fontWeight: 400 }}>→</span>
                  <span style={{
                    color: 'var(--text-main)', fontWeight: 600, fontSize: 'var(--fs-body)',
                  }}>
                    {formatLen(f.valor_mesurat_cm, unit)}
                  </span>
                </>
              )}
            </div>
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>
              {colocat && f.valor_mesurat_cm != null
                ? `${t('pattern.taller.value_sheet_t')} → ${t('pattern.taller.value_pattern_t')}`
                : t('pattern.taller.value_sheet_t')}
            </div>
          </div>

          {colocat && f.valor_mesurat_cm != null && f.delta_cm != null && (
            <XipVeredicte t={t} estat={estat} delta={f.delta_cm} unit={unit} />
          )}
          {colocat && f.valor_mesurat_cm == null && (
            <span style={{
              color: 'var(--err)', fontWeight: 600, fontSize: 'var(--fs-caption)',
            }}>
              {t('pattern.pom_unmeasured')}
            </span>
          )}
        </div>
      </button>

      <BotoInfo t={t} lang={lang} f={f} obert={obert} onInfo={onInfo} onTanca={onTanca} />
      <MenuAccions
        t={t} obert={menuObert} onObre={onMenu} onTanca={onTancaMenu}
        accions={[
          // ⚠️ «Col·locar» NO hi entra (NORMA §5.6: el menú ⋯ és per a accions ocasionals,
          // MAI per a passos de flux). Col·locar és EL pas de flux d'aquesta pantalla, i la
          // fila sencera ja és aquest botó: posar-l'hi hauria estat duplicar-lo i amagar-lo.
          ...(f.ancoratges || []).map(anc => {
            const pom = pomPerId?.get(anc.pattern_pom)
            const on = (f.ancoratges.length > 1 || !colocat) ? ` · ${anc.peca}` : ''
            return [
              onAssenyala && {
                // `ti-focus-2` i no `ti-eye`: l'ull ja vol dir «visible / amagat» a tot el
                // producte, i un ull barrat al costat d'una cota es llegiria com «amaga-la
                // del canvas», que és el contrari del que fa.
                icona: 'ti-focus-2',
                text: (pomSelId === anc.pattern_pom
                  ? t('pattern.taller.act_unpoint') : t('pattern.taller.act_point')) + on,
                fes: () => onAssenyala(anc.pattern_pom),
              },
              pom && onReobre && {
                icona: 'ti-pencil', text: t('pattern.taller.act_reanchor') + on,
                fes: () => onReobre(pom),
              },
              onEsborra && {
                icona: 'ti-trash', perillosa: true,
                text: t('pattern.taller.act_delete') + on,
                fes: () => onEsborra(anc.pattern_pom),
              },
            ]
          }).flat(),
        ]}
      />
    </div>
  )
}

/**
 * Un POM ancorat que la FITXA NO DEMANA (la via secundària).
 *
 * No té valor d'espec ni Δ ni veredicte, i no en pot tenir: no hi ha res amb què comparar-lo.
 * Ensenya el que sí que se'n sap —què mesura, sobre quina peça— i les mateixes accions.
 */
function FilaForana({
  t, p, unit, sel, menuObert, onMenu, onTancaMenu, onReobre, onEsborra, onAssenyala,
}) {
  return (
    <div style={{
      position: 'relative',
      background: sel ? 'var(--sel)' : 'var(--panel)',
      border: `1px solid ${sel ? 'var(--gold)' : 'var(--line)'}`,
      // Igual que a `Fila`: seleccionada mana el filet d'or (NORMA §4); si no, el gris que
      // diu que aquest ancoratge no és de la fitxa.
      borderLeft: `3px solid ${sel ? 'var(--gold)' : 'var(--text-soft)'}`,
      borderRadius: 4, display: 'flex', alignItems: 'center',
      padding: '0.3rem 0.5rem', gap: '0.5rem',
    }}>
      <i className="ti ti-circle-check" style={{ color: 'var(--text-soft)', flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 'var(--fs-body)', fontWeight: 600, fontFamily: 'var(--mono)',
        }}>
          {p.pom_code}
        </div>
        <div style={{
          fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {[p.pom_nom, p.peca].filter(Boolean).join(' · ')}
        </div>
      </div>
      <span
        title={titleLen(p.valor_mesurat_cm)}
        style={{
          fontFamily: 'var(--mono)', fontSize: 'var(--fs-body)', fontWeight: 600,
          // El mateix vermell que a `Fila`: la mateixa condició al mateix panell no es pot
          // pintar de dos colors.
          color: p.valor_mesurat_cm == null ? 'var(--err)' : 'var(--text-main)',
          flexShrink: 0,
        }}
      >
        {p.valor_mesurat_cm != null
          ? formatLen(p.valor_mesurat_cm, unit)
          : t('pattern.pom_unmeasured')}
      </span>
      <MenuAccions
        t={t} obert={menuObert} onObre={onMenu} onTanca={onTancaMenu}
        accions={[
          onAssenyala && {
            icona: 'ti-focus-2',
            text: sel ? t('pattern.taller.act_unpoint') : t('pattern.taller.act_point'),
            fes: () => onAssenyala(p.id),
          },
          onReobre && {
            icona: 'ti-pencil', text: t('pattern.taller.act_reanchor'),
            fes: () => onReobre(p),
          },
          onEsborra && {
            icona: 'ti-trash', perillosa: true, text: t('pattern.taller.act_delete'),
            fes: () => onEsborra(p.id),
          },
        ]}
      />
    </div>
  )
}

/**
 * TOTES les accions d'una fila, en un sol lloc.
 *
 * Abans n'hi havia d'escampades: col·locar era la fila sencera i esborrar/reobrir vivien a
 * l'ALTRE panell, el d'ancorats, amb la seva pròpia selecció. Amb un panell únic, la fila
 * ha de poder-ho fer tot — i «tot» amb una fila estreta vol dir un desplegable, no sis
 * icones que no hi caben.
 *
 * Amb DOS ancoratges del mateix POM (l'amplada de pit mesurada al davant i a l'esquena) les
 * accions es repeteixen per peça i el rètol ho diu: són dues mesures diferents, no dues
 * versions de la mateixa.
 */
function MenuAccions({ t, obert, onObre, onTanca, accions }) {
  const box = useRef(null)
  const [lloc, setLloc] = useState(null)
  const vives = (accions || []).filter(Boolean)

  // 🚨 EL MENÚ SURT DEL PANELL PER UN PORTAL, i no és una floritura.
  //
  // El panell de POMs és una caixa d'scroll (`Contenidor` → `overflowY: 'auto'`), i el CSS
  // diu que un `overflow-y` que no sigui `visible` força l'`overflow-x` a `auto`: la caixa
  // RETALLA per tots quatre costats. Un `position: absolute` a dins hi queda tancat, i cap
  // `zIndex` no en salva —el retall passa abans que l'apilament. Mesurat sobre aquest
  // panell: un menú de tres ítems obert a una fila baixa cau 84 px fora de la caixa.
  //
  // Abans això era una molèstia; ara no ho és: amb la fusió de panells, aquest menú és
  // l'ÚNICA porta a esborrar, re-ancorar i assenyalar. Un menú retallat és una funció que no
  // existeix.
  //
  // Es reposiciona en obrir, i en scroll o resize es tanca en lloc de perseguir el botó:
  // seguir-lo demanaria escoltar l'scroll de tots els avantpassats, i un menú que es tanca
  // quan el terra es mou és el que qualsevol espera.
  // La posició es pren al CLIC, no a un efecte: mesurar i obrir passen a la mateixa tanda i
  // el menú neix ja col·locat. Fer-ho a un efecte volia dir un `setState` síncron a dins
  // (render en cascada) i, el primer fotograma, un menú a la posició de l'anterior.
  const obre = () => {
    const r = box.current?.getBoundingClientRect()
    if (r) setLloc({ dalt: r.bottom + 4, dreta: window.innerWidth - r.right })
    onObre()
  }

  useEffect(() => {
    if (!obert) return undefined
    const tanca = () => onTanca()
    window.addEventListener('scroll', tanca, true)
    window.addEventListener('resize', tanca)
    return () => {
      window.removeEventListener('scroll', tanca, true)
      window.removeEventListener('resize', tanca)
    }
  }, [obert, onTanca])

  useEffect(() => {
    if (!obert) return undefined
    // `stopPropagation`: el Taller té un listener d'Escape a `window` que CANCEL·LA el gest
    // de col·locació. Sense aturar-hi la tecla, tancar aquest menú amb Esc també avortaria
    // l'ancoratge que s'estigués fent — dues coses per una tecla, i només una demanada.
    const perTecla = e => {
      if (e.key !== 'Escape') return
      e.stopPropagation()
      onTanca()
    }
    // El menú ja no viu dins de `box` (se n'ha anat pel portal), així que «a fora» s'ha de
    // preguntar també a ell: sense això, clicar un ítem el tancaria abans d'executar-lo.
    const perClic = e => {
      if (box.current?.contains(e.target)) return
      if (e.target.closest?.('[data-menu-accions]')) return
      onTanca()
    }
    document.addEventListener('keydown', perTecla)
    document.addEventListener('mousedown', perClic)
    return () => {
      document.removeEventListener('keydown', perTecla)
      document.removeEventListener('mousedown', perClic)
    }
  }, [obert, onTanca])

  if (!vives.length) return null

  return (
    <div ref={box} style={{ position: 'relative', flexShrink: 0 }}>
      <button
        onClick={obre}
        aria-expanded={obert}
        aria-haspopup="menu"
        aria-label={t('pattern.taller.act_menu')}
        title={t('pattern.taller.act_menu')}
        style={{
          background: 'none', border: 'none', cursor: 'pointer', padding: '0.2rem 0.35rem',
          color: obert ? 'var(--gold)' : 'var(--text-soft)', display: 'flex',
        }}
      >
        <i className="ti ti-dots-vertical" />
      </button>
      {obert && lloc && createPortal((
        <div
          role="menu"
          data-menu-accions
          style={{
            position: 'fixed', top: lloc.dalt, right: lloc.dreta, zIndex: 3000,
            minWidth: 192,
            background: 'var(--panel)', border: '1px solid var(--line)',
            borderRadius: 'var(--r-ctrl)', padding: 4,
            boxShadow: '0 4px 16px rgba(0,0,0,0.10)',
            display: 'flex', flexDirection: 'column', gap: 4,
          }}
        >
          {vives.map((a, i) => (
            <button
              key={i} role="menuitem"
              onClick={() => { onTanca(); a.fes() }}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.4rem', textAlign: 'left',
                background: 'none', border: 'none', cursor: 'pointer',
                borderRadius: 4, padding: '0.3rem 0.5rem',
                fontSize: 'var(--fs-caption)',
                color: a.perillosa ? 'var(--err)' : 'var(--text-main)',
              }}
            >
              <i className={`ti ${a.icona}`} />
              {a.text}
            </button>
          ))}
        </div>
      ), document.body)}
    </div>
  )
}

/**
 * El VEREDICTE de tolerància: el color fa el judici, i la xifra no es tenyeix mai (T2).
 *
 * Un número vermell no diu si és vermell perquè està fora o perquè importa. Un xip vermell
 * al costat d'un número negre sí: el judici té el seu lloc i la dada té el seu.
 */
function XipVeredicte({ t, estat, delta, unit }) {
  if (estat == null) {
    // Sense tolerància no hi ha veredicte: es dona la xifra i no es jutja.
    return (
      <span style={{
        fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
        border: '1px solid var(--line)', borderRadius: 10, padding: '1px 6px',
        whiteSpace: 'nowrap',
      }}>
        Δ {formatDelta(delta, unit)}
      </span>
    )
  }
  return (
    <span
      title={estat ? t('pattern.taller.tol_in_t') : t('pattern.taller.tol_out_t')}
      style={{
        fontSize: 'var(--fs-caption)', fontWeight: 600, whiteSpace: 'nowrap',
        color: estat ? 'var(--ok)' : 'var(--err)',
        background: estat ? 'var(--ok-bg)' : 'var(--err-bg)',
        border: `1px solid ${estat ? 'var(--ok)' : 'var(--err)'}`,
        borderRadius: 10, padding: '1px 6px',
        display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
      }}
    >
      <i className={`ti ${estat ? 'ti-check' : 'ti-x'}`} />
      Δ {formatDelta(delta, unit)}
    </span>
  )
}

/**
 * La mini-fitxa del POM (T3): el que el catàleg canònic JA sap.
 *
 * **Un camp buit no és una línia buida: és cap línia.** El catàleg encara no té la recepta de
 * tots els POMs, i pintar «D'on a on: —» a cada fila ensenyaria que la mini-fitxa no serveix.
 * El dia que s'omplin, el popover s'encén sol: no hi ha cap camp nou a crear.
 */
function BotoInfo({ t, lang, f, obert, onInfo, onTanca }) {
  const box = useRef(null)
  const fitxa = f.fitxa_pom || {}

  useEffect(() => {
    if (!obert) return undefined
    const perTecla = e => { if (e.key === 'Escape') onTanca() }
    const perClic = e => { if (box.current && !box.current.contains(e.target)) onTanca() }
    document.addEventListener('keydown', perTecla)
    document.addEventListener('mousedown', perClic)
    return () => {
      document.removeEventListener('keydown', perTecla)
      document.removeEventListener('mousedown', perClic)
    }
  }, [obert, onTanca])

  const nomLocal = enIdioma(f.nom, lang)
  const linies = [
    [t('pattern.taller.pom_info_name_en'), f.nom?.en],
    // El nom local només si diu una cosa DIFERENT de l'anglès: repetir-lo no informa.
    [t('pattern.taller.pom_info_name_local'), nomLocal !== f.nom?.en ? nomLocal : ''],
    [t('pattern.taller.pom_info_category'), fitxa.categoria],
    [t('pattern.taller.pom_info_method'), fitxa.metode],
    [t('pattern.taller.pom_info_tolerance'),
      f.tolerancia_minus_cm != null && f.tolerancia_plus_cm != null
        ? `−${f.tolerancia_minus_cm} / +${f.tolerancia_plus_cm} cm` : ''],
    // LA RECEPTA: d'on a on es mesura. Buida fins que el catàleg la porti.
    [t('pattern.taller.pom_info_from'), fitxa.punt_inici],
    [t('pattern.taller.pom_info_to'), fitxa.punt_final],
    [t('pattern.taller.pom_info_ref'), fitxa.punt_referencia],
  ].filter(([, v]) => v)

  return (
    <div ref={box} style={{ position: 'relative', flexShrink: 0 }}>
      <button
        onClick={onInfo}
        aria-label={t('pattern.taller.pom_info', { codi: f.codi_client })}
        aria-expanded={obert}
        title={t('pattern.taller.pom_info', { codi: f.codi_client })}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          padding: '0.3rem 0.45rem', color: obert ? 'var(--gold)' : 'var(--text-soft)',
          display: 'flex', alignItems: 'center',
        }}
      >
        <i className="ti ti-info-circle" />
      </button>

      {obert && (
        <div
          role="dialog"
          style={{
            position: 'absolute', top: '100%', right: 0, marginTop: 4,
            // Per sobre del canvas (lliçó D3): un popover que cau sota una capa no existeix.
            zIndex: 3000,
            minWidth: 240, maxWidth: 320,
            background: 'var(--panel)', border: '1px solid var(--line)',
            borderRadius: 6, padding: '0.6rem 0.7rem',
            boxShadow: '0 6px 20px rgba(0,0,0,0.18)',
            textAlign: 'left', cursor: 'default',
          }}
        >
          <div style={{
            fontFamily: 'var(--mono)', fontWeight: 600, fontSize: 'var(--fs-body)',
            marginBottom: '0.35rem',
          }}>
            {f.codi_client}
            {f.codi_global && (
              <span style={{
                fontSize: 'var(--fs-caption)', fontWeight: 400,
                color: 'var(--text-soft)', marginLeft: '0.4rem',
              }}>
                {f.codi_global}
              </span>
            )}
          </div>

          {linies.length === 0 ? (
            <p style={{
              margin: 0, fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
            }}>
              {t('pattern.taller.pom_info_empty')}
            </p>
          ) : (
            <dl style={{ margin: 0, display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '2px 8px' }}>
              {linies.map(([etiqueta, valor]) => (
                <div key={etiqueta} style={{ display: 'contents' }}>
                  <dt style={{
                    fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
                    whiteSpace: 'nowrap',
                  }}>
                    {etiqueta}
                  </dt>
                  <dd style={{ margin: 0, fontSize: 'var(--fs-caption)' }}>{valor}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      )}
    </div>
  )
}
