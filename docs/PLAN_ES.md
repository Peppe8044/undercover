# Plan: el piloto de claims (versión en español)

Esta es una traducción para leer el plan. El plan que se sigue y donde se marcan los criterios es `docs/PLAN.md`. Los nombres técnicos (estados, operaciones, archivos) y los textos de la interfaz van en inglés, igual que en el producto.

El piloto viene de `docs/SPEC.md` y tiene tres partes:

- **Un backend.** Guarda la cola de claims y aplica la regla de firma (sign-off) para pagos sobre $1,000.
- **El UnderCover Agent.** Trabaja la cola a través de la API del backend.
- **Un dashboard.** Los handlers ven la cola, cada claim, los pasos del agente y sus instrucciones, y firman los pagos retenidos.

El trabajo se divide en seis fases, cada una construida sobre la anterior.

## Enfoque

### Estados de un claim

Un claim está en uno de los cuatro estados que nombra el spec:

| Estado | Etiqueta | Significado |
|---|---|---|
| `waiting` | Waiting | Cargado desde `data/claims.json`; el agente aún no lo empieza |
| `in_progress` | In progress | El agente está trabajando en él |
| `waiting_for_sign_off` | Waiting for sign-off | El agente aprobó un pago sobre $1,000 y el pago espera a un handler |
| `decided` | Decided | Rechazado, derivado, o aprobado y liquidado |

Una decisión es final. Para volver a correr el agente sobre un claim hay que resetear la base, con `uv run -m backend.seed`.

- **Por qué:** son los cuatro estados que el equipo pidió ver.
- **Por qué:** que las decisiones sean finales mantiene las reglas simples y el historial fiel.

### La regla de $1,000 la aplica el backend, no el prompt

Primero el agente registra su decisión con `decide_claim`. Pagar es una operación aparte, `pay_claim`, que recibe el monto. El backend acepta un pago solo si se cumple todo esto:

- El claim está aprobado.
- El monto es igual al pago aprobado.
- El claim no se pagó antes.
- Si el pago supera el límite de `data/company.json` ($1,000.00), un handler ya lo firmó. Si no, el backend rechaza el pago con 403.

La firma de un handler, `sign_off_claim` con su id, paga el monto aprobado y cierra el claim. El handler debe tener `can_approve_over_limit` en true.

- **Por qué:** el spec dice que el sistema debe bloquear el pago "aunque el agente intente pagar". Una regla en el prompt se puede ignorar; una regla en la API no.

### El agente lo obtiene todo a través de la API

El agente obtiene los claims, las pólizas, los clientes y sus propias instrucciones por HTTP. Nunca lee `data/`.

Las instrucciones viven en `backend/instructions.md`. El backend las entrega con el policy wording de `data/policy_wording.md` agregado al final, así el agente siempre lo tiene en su prompt. El dashboard muestra ese mismo texto, en solo lectura.

El manual de claims queda fuera, como pide el spec.

- **Por qué:** el tech stack lo exige.
- **Por qué:** además, así el dashboard muestra exactamente lo que se le dijo al agente.

### Los pasos del agente

`run()` transmite el trabajo del agente y envía cada paso al backend a medida que ocurre. Un paso es uno de estos:

- una llamada a una herramienta, con sus argumentos
- el resultado de una herramienta
- el texto del modelo

Mientras un claim está en curso, el dashboard actualiza sus pasos cada segundo.

- **Por qué:** el equipo necesita ver qué hace el agente mientras trabaja.
- **Por qué:** consultar una lista de pasos es la forma más simple de lograrlo, sin websockets.

### Almacenamiento

SQLite con el módulo estándar `sqlite3` de Python. Cada registro de origen guarda su JSON original en una columna, junto a las columnas que cambia el flujo: estado, decisión, pago, firma y pasos.

La base de datos es `backend/undercover.db`, o la ruta de la variable de entorno `UNDERCOVER_DB`. `*.db` ya está en `.gitignore`.

Al arrancar, el backend carga los datos si el archivo de la base aún no existe. `uv run -m backend.seed` la resetea en cualquier momento.

La carga lee solo estos archivos:

- `claims.json`
- `policies.json`
- `customers.json`
- `plans.json`
- `handlers.json`
- `company.json`

Nunca lee `data/evals/` ni `data/security/`.

- **Por qué:** cubre lo que necesita el piloto sin agregar dependencias.

### Cómo se corre el agente

`uv run -m agent` trabaja todos los claims en espera, en orden, con un thread id nuevo para cada uno. `uv run -m agent CLM-1001 CLM-1003` trabaja solo los claims indicados.

El agente no se lanza desde el dashboard, porque el spec pide que el equipo vea el trabajo, no que lo inicie.

### El dashboard

Tiene tres vistas, con rutas por hash: `#/`, `#/claims/CLM-1001` y `#/instructions`. Usan un hook pequeño sobre `location.hash`, así que no hace falta un paquete de rutas.

El estilo sigue `docs/BRAND.md`:

- Instrument Sans, Instrument Serif y JetBrains Mono, de Google Fonts.
- Colores como variables CSS, con un tema claro y uno oscuro según `prefers-color-scheme`.
- Paneles redondeados sin borde.
- Dinero como $1,250.00.

Los badges de estado siguen el orden de la marca:

| Estado | Color del badge | Texto |
|---|---|---|
| Decided | Sea Green | Midnight |
| Waiting | Marigold | Midnight |
| Waiting for sign-off | Coral | Midnight |
| In progress | Cerulean | Blanco |

### Los tests end-to-end usan su propio backend y su propia base

Playwright levanta un backend en el puerto 8001 con una base recién cargada, `e2e/undercover-e2e.db`, y un dashboard en el puerto 5174 que apunta a ese backend. Los tests hacen la parte del agente con llamadas a la API, así que nunca llaman a un modelo.

- **Por qué:** `npm run check` da el mismo resultado esté o no corriendo `npm run dev`.
- **Por qué:** los tests nunca cambian la cola con la que trabajas.

### Fuera del piloto

Quedan fuera, como dice el spec:

- el manual de claims
- el inicio de sesión
- los pagos reales
- los mensajes a clientes

También quedan fuera:

- puntuar contra `data/evals/`, que este build nunca abre
- `data/knowledge.json`
- el claim de seguridad

## La API

Cada operación tiene un `operation_id` y un docstring de una línea, y ninguna recibe entradas opcionales. Un test verifica las tres cosas contra el esquema OpenAPI.

| Método y ruta | `operation_id` | Entrada | Notas |
|---|---|---|---|
| `GET /api/health` | `health` | | Ya existe |
| `GET /api/claims` | `list_claims` | | Una fila por claim: id, nombre del cliente, tipo, resumen, monto reclamado, fecha de envío, estado, decisión, pago |
| `GET /api/claims/{claim_id}` | `get_claim` | | El claim completo, con su decisión, pago y firma |
| `GET /api/policies/{policy_id}` | `get_policy` | | La póliza con los límites de su plan y el detalle de sus add-ons |
| `GET /api/customers/{customer_id}` | `get_customer` | | El cliente con sus claims anteriores |
| `GET /api/handlers` | `list_handlers` | | Los tres handlers |
| `GET /api/instructions` | `get_instructions` | | `{"text": ...}`: las instrucciones del agente con el policy wording |
| `POST /api/claims/{claim_id}/start` | `start_claim` | `thread_id` | De `waiting` a `in_progress`; 409 desde cualquier otro estado |
| `POST /api/claims/{claim_id}/steps` | `add_step` | `kind`, `content` | `kind` es `model`, `tool_call` o `tool_result` |
| `GET /api/claims/{claim_id}/steps` | `list_steps` | | En orden, con hora |
| `POST /api/claims/{claim_id}/decision` | `decide_claim` | `decision`, `payout`, `reason`, `policy_section` | Solo desde `in_progress`; ver las reglas abajo |
| `POST /api/claims/{claim_id}/payment` | `pay_claim` | `amount` | Ver la regla de $1,000 arriba |
| `POST /api/claims/{claim_id}/sign-off` | `sign_off_claim` | `handler_id` | Solo desde `waiting_for_sign_off`; paga el monto y cierra el claim |

Reglas de `decide_claim`:

- Un rechazo o una derivación debe tener pago 0; si no, el backend responde 422. El claim pasa a `decided`.
- Una aprobación de $1,000.00 o menos pasa a `decided`, y después el agente paga.
- Una aprobación sobre $1,000.00 pasa a `waiting_for_sign_off`.

Errores:

- Un id desconocido responde 404.
- Una operación en el estado equivocado responde 409.

## Fase 1: los datos del backend y las operaciones de lectura

**Qué construye:**

- `backend/db.py`: la conexión, el esquema y la lógica de carga.
- `backend/seed.py`: el comando para resetear.
- Las operaciones de lectura: `list_claims`, `get_claim`, `get_policy`, `get_customer`, `list_handlers` y `get_instructions`.
- Una primera versión de `backend/instructions.md`.
- La carga al arrancar, cuando aún no hay archivo de base de datos.

**Por qué primero:** todo lo demás lee de aquí.

**Criterios de éxito:**

- `uv run -m backend.seed` crea `backend/undercover.db` e informa 25 claims, 50 pólizas, 49 clientes y 3 handlers.
- `GET /api/claims` devuelve 25 claims, de CLM-1001 a CLM-1025. Todos están en `waiting` y sin decisión.
- `GET /api/claims/CLM-1001` devuelve:
  - la historia
  - tres ítems que suman $420.00
  - cuatro documentos
  - el estado `waiting`
- `GET /api/policies/POL-2001` devuelve el plan Premium con un deducible de $50.00.
- `GET /api/customers/CUS-3001` devuelve a Maya Patel, con el claim anterior CLM-0412.
- `GET /api/handlers` devuelve a Dana Whitfield, Marcus Oyelaran y Priya Raman.
- `GET /api/instructions` devuelve un texto que contiene "Version 2026.1" del policy wording. El texto no menciona el manual de claims.
- Un id desconocido de claim, póliza o cliente responde 404.
- Un test revisa el esquema OpenAPI. Cada operación tiene un `operation_id`, una descripción de una línea y solo entradas obligatorias.
- Un test verifica que los ids cargados son exactamente CLM-1001 a CLM-1025, así no entra nada de `data/evals/` ni de `data/security/`.
- Si se borra el archivo de la base y se arranca el backend, los datos se cargan de nuevo.
- `npm run check:python` pasa con una cobertura de 80% o más.

## Fase 2: el flujo de un claim y la regla de $1,000

**Qué construye:**

- Estas operaciones:
  - `start_claim`
  - `add_step`
  - `list_steps`
  - `decide_claim`
  - `pay_claim`
  - `sign_off_claim`
- Los cambios de estado y las reglas descritas arriba.

**Por qué ahora:** la regla de firma pertenece al backend. Con las operaciones listas y probadas, el agente y el dashboard se construyen sobre un contrato fijo.

**Criterios de éxito:**

- **Inicio.** `start_claim` pasa un claim en espera a `in_progress` y registra el thread id. Una segunda llamada responde 409.
- **Pasos.** `add_step` seguido de `list_steps` devuelve los pasos en el orden en que se agregaron, cada uno con su hora.
- **Rechazo.** Un rechazo con pago 0 pasa el claim a `decided`. Un rechazo con pago responde 422.
- **Aprobación hasta el límite.**
  - Una aprobación de $420.00 pasa el claim a `decided`.
  - `pay_claim` con 420.00 registra el pago.
  - Un segundo pago responde 409.
  - Un pago por un monto distinto responde 422.
- **Justo en el límite.** Una aprobación de exactamente $1,000.00 pasa el claim a `decided`, y el pago funciona.
- **Sobre el límite.**
  - Una aprobación de $1,150.00 pasa el claim a `waiting_for_sign_off`.
  - `pay_claim` responde 403, con un mensaje que dice que el pago espera la firma de un handler, y no se paga nada.
- **Firma.**
  - `sign_off_claim` con HND-01 sobre ese claim registra a Dana Whitfield, paga $1,150.00 y pasa el claim a `decided`.
  - Un handler desconocido responde 404.
  - Firmar un claim que no espera firma responde 409.
- **Decisiones finales.** `decide_claim` sobre un claim decidido responde 409.
- **Reset.** `uv run -m backend.seed` devuelve todos los claims a `waiting` y borra sus pasos.
- `npm run check:python` pasa con una cobertura de 80% o más.

## Fase 3: el UnderCover Agent

**Qué construye:**

- **Las instrucciones**, en `backend/instructions.md`:
  - Leer el claim, la póliza y los claims anteriores del cliente.
  - Revisarlos contra el policy wording.
  - Decidir si aprueba, rechaza o deriva:
    - Derivar cuando falta un documento que el wording pide, o cuando el claim requiere un criterio que el wording no resuelve.
  - Calcular el pago como describe la sección 10 del wording.
  - Registrar la decisión con:
    - una razón de dos o tres oraciones
    - la sección de la póliza que aplica
  - Pagar una aprobación.
  - Detenerse si el pago queda retenido a la espera de firma.
- **Las herramientas**, cada una es una llamada a la API:
  - `get_claim`, `get_policy` y `get_customer`
  - `decide_claim` y `pay_claim`

  Una llamada rechazada devuelve al modelo el mensaje del backend, así el agente sabe que el pago quedó retenido. No se cae.
- **`run(claim_id, thread_id)`**, que trabaja un claim:
  1. Obtiene las instrucciones.
  2. Inicia el claim.
  3. Transmite el trabajo del agente y envía cada paso.
  4. Devuelve la respuesta final.
- **`agent/__main__.py`**, que recorre la cola.

**Por qué así:** el modelo se queda con el criterio: la decisión, el pago y la razón. El backend se queda con los controles. El piloto necesita un loop de agente simple con buenas herramientas, y el build de Week 1 Day 5 va a desarrollar el harness.

**Criterios de éxito:**

- **Aprobación hasta el límite.**
  - Con un modelo de prueba programado para leer CLM-1001, aprobar $420.00 y pagar, `run()` deja el claim en `decided` y pagado.
  - Sus pasos muestran cada llamada a herramienta y su resultado, en orden.
- **Sobre el límite.**
  - Con un modelo de prueba programado para aprobar CLM-1002 por $1,150.00 y luego pagar, el pago se rechaza.
  - El rechazo aparece como resultado de herramienta en los pasos, y el claim queda en `waiting_for_sign_off` y sin pagar.
- **Rechazo.** Con un modelo de prueba programado para rechazar, el claim queda en `decided` con pago 0.
- **Recorrido de la cola.** Con `run` reemplazado por uno de prueba, `uv run -m agent` toma solo los claims en espera, y con ids indicados toma solo esos.
- **Elección del modelo.** El modelo por defecto sigue siendo `openai/gpt-6-luna` con reasoning bajo, y `MODEL_NAME` lo reemplaza. El test existente sigue pasando.
- **Sin datos locales.** Una búsqueda de `data/` en `agent/` no encuentra nada.
- `npm run check:python` pasa con una cobertura de 80% o más.

## Fase 4: la cola y las instrucciones en el dashboard

**Qué construye:**

- Los estilos de la marca: fuentes, variables de color y temas claro y oscuro.
- Un encabezado con enlaces a la cola y a las instrucciones.
- **La página de la cola:**
  - El número de claims en cada estado.
  - Una tabla con id, cliente, tipo, resumen, monto reclamado, fecha de envío, badge de estado, decisión y pago.
  - Cada fila enlaza a su claim.
  - La tabla se actualiza cada dos segundos.
- **La página de instrucciones:** las instrucciones del agente como texto de solo lectura.
- **Formato compartido:** dinero como $1,250.00 y etiquetas para los tipos de claim y los estados.

Esto reemplaza la página de health.

**Por qué ahora:** la cola es la pantalla principal de los handlers y solo necesita las operaciones de lectura.

**Criterios de éxito:**

- **Tests unitarios.** Los tests de Vitest cubren:
  - la cola dibujada a partir de un fetch simulado
  - el conteo por estado
  - el formato del dinero
  - la página de instrucciones
  - un mensaje de error cuando el backend no responde
- **La cola en el navegador.** Con `npm run dev` y una carga recién hecha, revisado con el servidor MCP de Playwright:
  - `http://localhost:5173` muestra 25 claims, todos en Waiting.
  - CLM-1001 muestra $420.00.
- **Las instrucciones en el navegador.** `#/instructions` muestra las instrucciones y el policy wording, sin forma de editarlos.
- **Tema oscuro.** La página sigue la marca en modo oscuro: fondo `#04232E` y paneles negros.
- `npm run check:ts` pasa con una cobertura de 80% o más.

## Fase 5: la página de cada claim, los pasos del agente y la firma

**Qué construye:** la página del claim, con estas secciones:

- **El claim:** id, estado, cliente, tipo, fechas, lugar y monto reclamado.
- **La historia.**
- **Los ítems**, en una tabla.
- **Los documentos.**
- **La póliza:** plan, add-ons, fechas del viaje, costo del viaje y viajeros.
- **Los claims anteriores del cliente.**
- **La decisión del agente:** la decisión, el pago, la razón, la sección de la póliza y el estado del pago, que es uno de estos:
  - Paid
  - Waiting for sign-off
  - Not paid
- **El panel de firma**, cuando el claim espera firma. Tiene un selector de handler y un botón "Sign off and pay".
- **Los pasos del agente.** Se actualizan cada segundo mientras el claim está en curso.

**Por qué ahora:** esta página necesita las operaciones de lectura y las de escritura de la Fase 2.

**Criterios de éxito:**

- **Tests unitarios.** Los tests de Vitest cubren:
  - un claim en espera
  - un claim decidido, con su razón
  - un claim que espera firma y se firma
  - la lista de pasos
- **El claim en el navegador.** `#/claims/CLM-1001` muestra:
  - la historia
  - tres ítems
  - cuatro documentos
  - la póliza Premium
  - el claim anterior CLM-0412
- **Los pasos mientras trabaja el agente.** Llamando a la API como lo hace el agente, el navegador muestra cada paso poco después de agregarlo, sin recargar:
  - iniciar CLM-1001
  - agregar pasos
  - aprobar $420.00
  - pagar
- **El claim terminado.** Después el claim muestra Decided, la razón, la sección de la póliza y "Paid $420.00".
- **La firma en el navegador.**
  - Aprobar CLM-1002 por $1,150.00 a través de la API.
  - La página muestra "Waiting for sign-off".
  - Un pago a través de la API se rechaza.
  - Al firmar como Priya Raman en el navegador, se ve Decided, "Paid $1,150.00" y su nombre.
- **Reset.** `uv run -m backend.seed` resetea la cola después de estas pruebas.
- `npm run check:ts` pasa con una cobertura de 80% o más.

## Fase 6: tests end-to-end, una corrida real y la entrega

**Qué construye:**

- **Servidores propios para Playwright.** Playwright levanta un backend con datos cargados en el puerto 8001 y un dashboard en el puerto 5174.
  - El destino del proxy de vite viene de `UNDERCOVER_API_URL`, con `http://127.0.0.1:8000` por defecto.
- **Tests end-to-end**, que reemplazan el test de health. Cubren:
  - la cola
  - la página de un claim
  - una aprobación hasta el límite que el agente paga
  - una aprobación sobre el límite, con el pago rechazado y firmada en el navegador
  - los pasos
  - las instrucciones
- **`docs/STATUS.md`:** qué está construido y cómo correrlo.

**Por qué al final:** los tests end-to-end revisan el flujo completo una vez que existen todas las partes, y la corrida real prueba el modelo de verdad con claims reales.

**Criterios de éxito:**

- `npm run e2e` pasa. Pasa también en una segunda corrida, porque cada corrida empieza con una base nueva.
- `npm run e2e` pasa con `npm run dev` corriendo al mismo tiempo, y la cola de desarrollo no cambia.
- **Corrida real con tu key de OpenRouter.** Esto llama al modelo y cuesta unos centavos.
  - Resetear, correr `npm run dev` y luego `uv run -m agent CLM-1001 CLM-1003`.
  - El dashboard muestra los pasos mientras se trabaja cada claim.
  - Cada claim termina en `decided` o en `waiting_for_sign_off`, con:
    - una decisión
    - una razón de dos o tres oraciones
    - una sección de la póliza
    - un pago, si se aprobó
  - Toda aprobación sobre $1,000 muestra un pago rechazado en sus pasos y espera firma.
- **Reset después de la corrida real.** `uv run -m backend.seed` resetea la cola al terminar.
- **Archivo de estado.** `docs/STATUS.md` describe:
  - el backend, el agente y el dashboard
  - los estados de un claim y la regla de firma
  - los comandos `npm run dev`, `uv run -m agent`, `uv run -m backend.seed` y `npm run check`
- `npm run check` pasa: ruff, pyright, pytest, ESLint, Prettier, tsc, vitest y Playwright.
