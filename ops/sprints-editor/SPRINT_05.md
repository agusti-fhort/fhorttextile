# SPRINT 05 — FTTPT fase 2: camps col·locables (placeholders) i resolució
FRONTEND + backend lleu. Depèn de S4.

## Llei (Agus)
Placeholder es resol EN INSTANCIAR la plantilla amb dades del model i QUEDA TEXT/IMATGE
(mateix gest snapshot). Mai binding viu.

## Abast
1. ELEMENT PLACEHOLDER: { type:'field', key:'<camp>', label, x,y, style } — només té
   sentit dins d'un kind=template. Al llenç de plantilla es pinta com a xip/etiqueta
   distintiva ({Nom del model}, vora puntejada gold).
2. PANELL DE CAMPS (només en editar plantilla): llista col·locable per drag/clic.
   Catàleg v1 (de ModelDetailSerializer, verificat §4.4): nom_prenda · codi_intern ·
   codi_client · customer_nom · collection · temporada+any · color_referencia ·
   descripcio · responsable_nom · data_entrada · base_size_label · size_system_nom ·
   fabric_main · fabric_composition · **customer_logo (IMATGE)** · data d'avui.
   (No existeixen marca/dissenyador/patronista dedicats — NO inventar-los.)
3. RESOLUCIÓ: al flux "nou document des de plantilla" (S4), recórrer objects
   type:'field' → substituir per type:'text' amb el valor real del model (o type:'image'
   per al logo, descarregant l'asset dins del zip .ftt). Camp buit al model → text buit
   + avís no bloquejant. La resolució viu al frontend (ja té el ModelDetail carregat)
   o backend si el create_document és server-side — decidir a la mini-diagnosi segons
   on va quedar S4; el simple guanya.
4. Un type:'field' residual dins d'un kind=document (cas límit) es pinta com a text
   literal del label — mai crash.

## Porta verda
Plantilla amb 5 camps + logo → nou document del model 188 → tot resolt com a text/imatge
estàtics; el JSON resultant NO conté cap type:'field'. Export PDF correcte. i18n de les
etiquetes del panell. Build (+check si backend) nets.

## Commits: 1. element field + panell · 2. resolució en instanciar · 3. logo com a asset.
