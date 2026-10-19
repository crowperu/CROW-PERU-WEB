# CROW TRY ON — plan de validación y recursos (prototipo)
Estado: desarrollo aislado; no desplegado ni validado en dispositivos.
## Alcance
- Cámara frontal con consentimiento y selfie local; no subir imágenes ni enviar datos faciales a Supabase.
- Primeros modelos de prueba: argolla, colgante y punto dorado (ilustraciones; NO SKU reales).
- Próximo objetivo: seguimiento facial y calibración de orejas con MediaPipe Face Landmarker, sujeto a pruebas de precisión y licencia.
## Recursos requeridos por SKU
- Identificador existente de producto, imagen de frente con fondo transparente, medidas en milímetros, par simétrico/asimétrico, posición de anclaje y autorización para mostrar en probador.
- PNG o WebP transparente, idealmente 1024 x 1024 px como fuente; optimizar peso para web.
- Si la foto existente no permite un recorte preciso: una toma frontal por diseño simétrico; dos para asimétricos; lateral opcional en colgantes.
## Puertas de calidad
1. Inspección de arquitectura real de storefront antes de integrar; repositorio actual puede no ser el que despliega.
2. Safari iOS, Chrome Android, escritorio: permisos, denegación, cierre de cámara, orientación, selfie, guardar y errores.
3. Sin red para subir selfie; comprobar con panel Network. Detener tracks al cerrar o cambiar a foto.
4. Verificar tamaño/posición y oclusión de cabello; no afirmar precisión física sin calibración.
5. Performance: carga diferida, sin degradar LCP/CLS de producto.
6. Seguridad: no modificar checkout, pagos, SUNAT, inventario, CRM, ni RLS; feature flag OFF por defecto.
7. QA y rollback antes de cualquier merge/deploy. Revisar cuotas de GitHub Actions y Cloudflare.
## Pendientes
- Auditar catálogo y fotos reales, seleccionar 5 SKUs.
- Implementar tracking automático (no disponible en el prototipo actual).
- Validar descarga en iOS/Android; en iOS podría requerirse compartir en vez de descarga directa.
- Corregir correspondencia visual de canvas con object-fit/letterboxing para distintos tamaños de pantalla.
- Habilitar preview seguro y confirmar que no expone datos ni altera la tienda.
