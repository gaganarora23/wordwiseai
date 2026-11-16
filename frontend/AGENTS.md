## WordWise service boundary
- Keep vocabulary selection and persistence behind `WordWiseService`; screens use the mock implementation until a real service is requested, so UI and service logic remain independently replaceable.
- Narrow optional grades, words, and selections before service calls or rendering; missing saved values must show a recoverable error instead of crashing the learning flow.
