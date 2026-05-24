<?php
/**
 * Script para limpiar acciones fallidas de Action Scheduler
 * Sube este archivo al directorio raíz de WordPress y accede vía navegador
 * IMPORTANTE: Bórralo después de usarlo por seguridad
 */

// Seguridad básica - cambia esto por algo único
define('CLEANUP_KEY', 'tu_clave_segura_12345');

if (!isset($_GET['key']) || $_GET['key'] !== CLEANUP_KEY) {
    die('Acceso denegado. Usa: ?key=tu_clave_segura_12345');
}

// Cargar WordPress
require_once(__DIR__ . '/wp-load.php');

if (!function_exists('as_unschedule_all_actions')) {
    die('Action Scheduler no está disponible.');
}

echo "<h2>Limpieza de Action Scheduler - WooCommerce</h2>";
echo "<pre>";

// 1. Hooks problemáticos identificados
$problematic_hooks = [
    'action_scheduler/migration_hook',
    'rank_math/analytics/data_fetch'
];

echo "=== PASO 1: Cancelando acciones fallidas específicas ===\n";
foreach ($problematic_hooks as $hook) {
    $count = as_unschedule_all_actions($hook);
    echo "✓ Canceladas {$count} acciones de: {$hook}\n";
}

// 2. Limpiar acciones fallidas antiguas (más de 1 día)
echo "\n=== PASO 2: Limpiando acciones fallidas antiguas ===\n";
global $wpdb;
$table = $wpdb->prefix . 'actionscheduler_actions';

// Contar antes
$failed_count = $wpdb->get_var(
    "SELECT COUNT(*) FROM {$table} 
     WHERE status = 'failed' 
     AND scheduled_date_gmt < DATE_SUB(NOW(), INTERVAL 1 DAY)"
);
echo "Encontradas {$failed_count} acciones fallidas antiguas\n";

// Eliminar
if ($failed_count > 0) {
    $deleted = $wpdb->query(
        "DELETE FROM {$table} 
         WHERE status = 'failed' 
         AND scheduled_date_gmt < DATE_SUB(NOW(), INTERVAL 1 DAY) 
         LIMIT 500"
    );
    echo "✓ Eliminadas {$deleted} acciones fallidas\n";
}

// 3. Resetear acciones "in-progress" atascadas (más de 1 hora)
echo "\n=== PASO 3: Reseteando acciones atascadas ===\n";
$stuck = $wpdb->get_var(
    "SELECT COUNT(*) FROM {$table} 
     WHERE status = 'in-progress' 
     AND scheduled_date_gmt < DATE_SUB(NOW(), INTERVAL 1 HOUR)"
);
echo "Encontradas {$stuck} acciones atascadas\n";

if ($stuck > 0) {
    $reset = $wpdb->query(
        "UPDATE {$table} 
         SET status = 'pending' 
         WHERE status = 'in-progress' 
         AND scheduled_date_gmt < DATE_SUB(NOW(), INTERVAL 1 HOUR)"
    );
    echo "✓ Reseteadas {$reset} acciones a 'pending'\n";
}

// 4. Limpiar logs antiguos (opcional, más de 7 días)
echo "\n=== PASO 4: Limpiando logs antiguos ===\n";
$logs_table = $wpdb->prefix . 'actionscheduler_logs';
$old_logs = $wpdb->query(
    "DELETE FROM {$logs_table} 
     WHERE log_date_gmt < DATE_SUB(NOW(), INTERVAL 7 DAY) 
     LIMIT 1000"
);
echo "✓ Eliminados {$old_logs} logs antiguos\n";

// 5. Verificar estado actual
echo "\n=== ESTADO ACTUAL ===\n";
$stats = $wpdb->get_results(
    "SELECT status, COUNT(*) as count 
     FROM {$table} 
     GROUP BY status",
    ARRAY_A
);

foreach ($stats as $stat) {
    echo "{$stat['status']}: {$stat['count']} acciones\n";
}

echo "\n✅ LIMPIEZA COMPLETADA\n";
echo "\nPasos siguientes:\n";
echo "1. Ve a WooCommerce → Estado → Acciones programadas y verifica\n";
echo "2. Haz un pedido de prueba\n";
echo "3. IMPORTANTE: Elimina este archivo (woocommerce_cleanup.php) del servidor\n";
echo "</pre>";
?>
