# Evaluación del motor sobre lotes sintéticos

## Detección por tipo de defecto

| Código | Unidades sembradas | Detectadas | Detección | Falsos positivos |
|---|---:|---:|---:|---:|
| D01 | 4 | 4 | 100.0 % | 0 |
| D02 | 2 | 2 | 100.0 % | 0 |
| D03 | 2 | 2 | 100.0 % | 0 |
| D04 | 5 | 5 | 100.0 % | 0 |
| D05 | 4 | 4 | 100.0 % | 0 |
| D06 | 3 | 3 | 100.0 % | 0 |
| D07 | 6 | 6 | 100.0 % | 0 |
| D08 | 5 | 5 | 100.0 % | 0 |
| D09 | 5 | 5 | 100.0 % | 0 |
| D10 | 7 | 7 | 100.0 % | 0 |
| D11 | 9 | 9 | 100.0 % | 0 |
| D12 | 14 | 14 | 100.0 % | 0 |

## Resumen

| Métrica | Resultado |
|---|---:|
| Detección global | 100.0 % (66 de 66) |
| Tasa de falsos positivos | 0.0 % |
| Exactitud de disposición | 100.0 % |
| Disposiciones incorrectas | 0 |
| Precisión de candidatas D05 (determinística) | 100.0 % |
| Precisión de mapeos sugeridos por IA | N/A (se mide con `--with-ai`; la IA se integra en el incremento 5) |

## Tiempo por lote (motor determinístico)

| Lote | Archivos | Tiempo |
|---|---:|---:|
| batch_00_clean | 4 | 80.4 ms |
| batch_01_old_template | 4 | 52.8 ms |
| batch_02_wrong_files | 5 | 44.5 ms |
| batch_03_approvals | 4 | 78.4 ms |
| batch_04_partial | 5 | 30.9 ms |
| batch_05_mixed | 4 | 42.2 ms |
