# Exporting ProfitChart Backtest CSV

## Trade list (recommended for hybrid compare)

1. Open **Editor de Estratégias** → run **Backtest** (Tick-a-Tick when possible)
2. Open the **Operações** / trades tab in the report
3. **Exportar CSV** (or Excel → Save As CSV)
4. Enable **Aplicar formatação dos dados** if offered

Expected columns (Portuguese):

| Column | Aliases accepted |
|--------|------------------|
| Data | Data, Hora, Data/Hora |
| Ativo | Ativo, Symbol |
| Tipo | Compra/Venda, Tipo |
| Quantidade | Qtd, Contratos |
| Preço | Preço, Preco |
| Resultado | P/L, Lucro, Resultado |

Entry legs often show `Resultado = 0`; the parser ignores those and counts closed trades only.

## Summary report

Export the performance summary as two-column CSV:

```
Métrica;Valor
Total de Operações;85
Taxa de Acerto;58,82%
Resultado Líquido;1.250,50
...
```

## Upload in dashboard

**Backtest & Optimize** → Upload CSV → **Upload & Preview** → **Run Backtest** with engine `profit` or `compare`.

## API

```bash
curl -X POST http://localhost:8000/api/v1/backtest/upload \
  -F "file=@meu_backtest.csv"
```

Returns `{ "path": "...", "preview": { metrics... } }`.

## File format notes

- Separator: `;` (Brazilian default) or `,`
- Encoding: `latin-1` or `utf-8`
- Decimals: `1.234,56` (Brazilian) supported

If parsing fails, open an issue with a **redacted** sample (first 5 rows) so we can add column aliases.
