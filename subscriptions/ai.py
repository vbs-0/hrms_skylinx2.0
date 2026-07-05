"""Role-scoped AI assistant.

Security model (do not weaken):
- The browser only ever sends {message, history}; the server decides the role
  and builds the data context. The client cannot request another scope.
- Context builders are additive by role: employee sees ONLY their own rows,
  HR adds company-level HR data, CEO adds company-level totals. Everything is
  filtered by the requ