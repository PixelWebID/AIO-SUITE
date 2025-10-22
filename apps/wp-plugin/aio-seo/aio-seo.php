<?php
/**
 * Plugin Name: AIO Content Suite
 * Description: WordPress plugin for the AIO Suite project.  This plugin
 *   registers an admin page and a basic REST endpoint for demonstration.
 * Version: 0.1.0
 * Author: AIO Team
 */

// Exit if accessed directly.
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Main plugin class.
 */
class AIO_Content_Suite {
    /**
     * Constructor: hooks into WordPress actions.
     */
    public function __construct() {
        add_action('admin_menu', [$this, 'register_menu']);
        add_action('admin_enqueue_scripts', [$this, 'enqueue_assets']);
        add_action('rest_api_init', [$this, 'register_routes']);
    }

    /**
     * Register the main admin menu for AIO Suite.
     */
    public function register_menu() {
        add_menu_page(
            'AIO Suite',
            'AIO Suite',
            'manage_options',
            'aio-suite',
            [$this, 'render_page'],
            'dashicons-admin-generic'
        );
    }

    /**
     * Render the admin page content.
     */
    public function render_page() {
        echo '<div class="wrap">';
        echo '<h1>AIO Suite</h1>';
        echo '<div id="aio-root">Loading...</div>';
        echo '</div>';
    }

    /**
     * Enqueue assets (JavaScript) for the admin page.
     */
    public function enqueue_assets($hook) {
        // Only load on our plugin page.
        if (strpos($hook, 'aio-suite') === false) {
            return;
        }
        wp_enqueue_script(
            'aio-admin',
            plugin_dir_url(__FILE__) . 'src/admin.js',
            [],
            '0.1.0',
            true
        );
    }

    /**
     * Register custom REST routes.
     */
    public function register_routes() {
        register_rest_route(
            'aio/v1',
            '/ping',
            [
                'methods' => 'GET',
                'permission_callback' => '__return_true',
                'callback' => function () {
                    return [
                        'ok' => true,
                        'time' => time(),
                    ];
                },
            ]
        );
    }
}

// Initialize the plugin.
new AIO_Content_Suite();