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
    private const VERSION = '0.1.0';
    private const MENU_SLUG = 'aio-suite';

    /**
     * Constructor: hooks into WordPress actions.
     */
    public function __construct() {
        add_action('admin_menu', [$this, 'register_menu']);
        if (is_multisite()) {
            add_action('network_admin_menu', [$this, 'register_network_menu']);
        }
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
            self::MENU_SLUG,
            [$this, 'render_page'],
            'dashicons-admin-generic'
        );

        add_submenu_page(
            self::MENU_SLUG,
            'AIO Suite Settings',
            'Settings',
            'manage_options',
            self::MENU_SLUG . '-settings',
            [$this, 'render_settings_page']
        );
    }

    /**
     * Register network admin menu for multisite installations.
     */
    public function register_network_menu() {
        add_menu_page(
            'AIO Suite Network',
            'AIO Suite',
            'manage_network_options',
            self::MENU_SLUG . '-network-settings',
            [$this, 'render_settings_page'],
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
     * Render settings page content for site or network admins.
     */
    public function render_settings_page() {
        echo '<div class="wrap">';
        echo '<h1>AIO Suite Settings</h1>';
        echo '<div id="aio-settings-root">Loading...</div>';
        echo '</div>';
    }

    /**
     * Enqueue assets (JavaScript) for the admin page.
     */
    public function enqueue_assets($hook) {
        $admin_hook = 'toplevel_page_' . self::MENU_SLUG;
        $settings_hook = self::MENU_SLUG . '_page_' . self::MENU_SLUG . '-settings';
        $network_hook = 'toplevel_page_' . self::MENU_SLUG . '-network-settings';

        if ($hook === $admin_hook) {
            $this->enqueue_admin_bundle();
        }

        if ($hook === $settings_hook || $hook === $network_hook) {
            $this->enqueue_settings_bundle();
        }
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

    /**
     * Enqueue assets for the dashboard/editor view.
     */
    private function enqueue_admin_bundle() {
        wp_enqueue_script(
            'aio-admin',
            plugin_dir_url(__FILE__) . 'src/admin.js',
            [],
            self::VERSION,
            true
        );
        wp_script_add_data('aio-admin', 'type', 'module');

        wp_enqueue_style(
            'aio-admin-style',
            plugin_dir_url(__FILE__) . 'src/style.css',
            [],
            self::VERSION
        );
    }

    /**
     * Enqueue assets for the settings view.
     */
    private function enqueue_settings_bundle() {
        wp_enqueue_script(
            'aio-settings',
            plugin_dir_url(__FILE__) . 'src/settings.js',
            [],
            self::VERSION,
            true
        );
        wp_script_add_data('aio-settings', 'type', 'module');

        wp_enqueue_style(
            'aio-admin-style',
            plugin_dir_url(__FILE__) . 'src/style.css',
            [],
            self::VERSION
        );
    }
}

// Initialize the plugin.
new AIO_Content_Suite();
