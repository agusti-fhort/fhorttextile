# Llista tancada de pantalles — extreta de l'inventari visual S37

Extracció literal de `INVENTARI_VISUAL_PANTALLES_S37.md`. **Cap pantalla afegida, cap
eliminada, cap reordenada.** Ordre exactament el de l'original.

**Tres avisos sobre la font, per no fer-te perdre temps al xat d'arquitectura:**

1. **La llista NO és al §1, és al §0** («Cens de pantalles — la llista tancada»). El §1
   és el resum executiu. La llista entregada aquí és la del §0.
2. **L'inventari NO registra «com s'hi arriba».** Només la ruta. No hi ha cap columna de
   navegació, de menú ni de procedència, o sigui que aquesta dada **no s'ha pogut
   entregar** sense inventar-la.
3. **L'inventari NO distingeix quines són «de servei / fora de menú».** El §0 anomena les
   31 «pantalles de servei arribables sense paràmetre» **totes juntes**, com un sol grup;
   no hi ha cap marca que en separi unes de les altres. Aquesta dada **tampoc s'ha pogut
   entregar**.

El que SÍ que porta l'inventari i s'ha afegit: la marca de referència 🔶 (§2) i el
recompte de colors literals 🚩 (§5). El nom del component ve del mateix document (§4 i §5),
unit a la ruta per `App.jsx:295-425`, que és la font que el §0 cita.

---

```
LLISTA TANCADA — 31 pantalles (inventari visual S37)
De les 58 rutes que declara el router (App.jsx:295-425).

 #   RUTA                              COMPONENT              MARQUES
 --  --------------------------------  ---------------------  ------------------------
  1  /                                 Dashboard
  2  /models                           Models                 🔶 REFERÈNCIA · 🚩 4
  3  /models/nou                       ModelWizard            🚩 5
  4  /fitxa-tecnica                    TechSheetEntry
  5  /fittings                         FittingSessionList     🚩 2
  6  /task-types                       TaskTypes
  7  /garment-types                    GarmentTypes
  8  /cataleg-peces                    CatalegPeces
  9  /suppliers                        Suppliers
 10  /recursos                         Recursos
 11  /encarrecs                        Encarrecs
 12  /clients                          Customers
 13  /comercial/productes              Products
 14  /comercial/ofertes                Quotes
 15  /comercial/condicions-pagament    PaymentTerms
 16  /comercial/comandes               Orders
 17  /comercial/encarrecs              WorkOrders
 18  /comercial/orfes                  OrphanedWorkOrders     🚩 1
 19  /comercial/albarans               DeliveryNotes          🚩 1
 20  /planificacio                     Planning               🚩 1
 21  /planificacio/calendari           PlanningCalendar       🚩 17
 22  /temps                            TimeTracking
 23  /poms                             POMs (→ POMCataleg)
 24  /poms/grading                     GradingRuleSets        🚩 46
 25  /size-library                     SizeLibrary            🚩 7
 26  /disseny/documents                DissenyPlaceholder
 27  /configuracio/general             GeneralConfig
 28  /configuracio/usuaris             UsersRoles             🚩 13
 29  /configuracio/calendari           CompanyCalendar
 30  /perfil                           UserProfilePage
 31  /onboarding                       OnboardingWizard       🚩 17

LLEGENDA
  🔶 REFERÈNCIA = la pantalla que l'Agus cita com a patró de mides (§2 de l'inventari).
  🚩 <n>        = colors literals (hex/rgba crus, no-token) al fitxer de la pantalla (§5).
                  Les 21 pantalles sense marca en tenen ZERO.
                  El comptador és un MÍNIM: ui/Card.jsx injecta 2 hex crus a qui la
                  consumeix (FittingSessionList, TimeTracking, UserProfilePage) que el
                  grep del fitxer de pantalla no veu.

  Total de colors literals vius: ~110 · el 73% en 4 fitxers (24, 21, 31, 28).

EXCLOSES DE LA LLISTA (les 27 restants de les 58 rutes), tal com les descriu el §0:
  · pantalles de detall amb :id (models/:id, clients/:id, comercial/*/:id…)
  · rutes fora del Shell (/login, /entrar, /reset-password/:uid/:token, la fitxa,
    el .ftt, el taller de patró, el fitting a pantalla completa)
  · redireccions (MesuresRedirect, SizeCheckRedirect, models/nou-des-de-fitxer, *)

NO REGISTRAT PER L'INVENTARI (no s'ha pogut entregar sense inventar-ho):
  · com s'hi arriba a cada pantalla (navegació/menú)
  · quines són «de servei / fora de menú» — el §0 les tracta totes com un sol grup
```
