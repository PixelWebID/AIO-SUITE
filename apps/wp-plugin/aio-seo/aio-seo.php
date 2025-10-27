<?php
/**
 * Plugin Name: AIO Content Suite
 * Description: Admin interface and REST bridge for the AIO Suite content automation platform.
 * Version: 0.2.0
 * Author: AIO Team
 */

if (!defined('ABSPATH')) {
    exit;
}

class AIO_Content_Suite {
    private const VERSION = '0.2.0';
    private const MENU_SLUG = 'aio-suite';
    private const OPTION_KEY = 'aio_suite_settings';
    private const REST_NAMESPACE = 'aio/v1';

    public function __construct() {
        add_action('admin_menu', [$this, 'register_menu']);
        if (is_multisite()) {
            add_action('network_admin_menu', [$this, 'register_network_menu']);
        }
        add_action('admin_enqueue_scripts', [$this, 'enqueue_assets']);
        add_action('rest_api_init', [$this, 'register_routes']);
    }

    public static function activate(): void {
        if (!get_option(self::OPTION_KEY)) {
            update_option(
                self::OPTION_KEY,
                [
                    'content_intel_url' => 'http://localhost:8000',
                    'social_hub_url' => 'http://localhost:8080',
                    'default_provider' => 'openai',
                    'auto_publish' => false,
                    'sites' => [],
                    'encrypted_api_key' => '',
                    'has_api_key' => false,
                ]
            );
        }
    }

    public function register_menu(): void {
        add_menu_page(
            __('AIO Suite', 'aio-suite'),
            __('AIO Suite', 'aio-suite'),
            'manage_options',
            self::MENU_SLUG,
            [$this, 'render_page'],
            'dashicons-media-spreadsheet',
            80
        );

        add_submenu_page(
            self::MENU_SLUG,
            __('AIO Suite Settings', 'aio-suite'),
            __('Settings', 'aio-suite'),
            'manage_options',
            self::MENU_SLUG . '-settings',
            [$this, 'render_settings_page']
        );
    }

    public function register_network_menu(): void {
        add_menu_page(
            __('AIO Suite Network', 'aio-suite'),
            __('AIO Suite', 'aio-suite'),
            'manage_network_options',
            self::MENU_SLUG . '-network-settings',
            [$this, 'render_settings_page'],
            'dashicons-media-spreadsheet'
        );
    }

    public function render_page(): void {
        echo '<div class="wrap">';
        echo '<h1>' . esc_html__('AIO Suite Workspace', 'aio-suite') . '</h1>';
        echo '<div id="aio-root">' . esc_html__('Loading interface…', 'aio-suite') . '</div>';
        echo '</div>';
    }

    public function render_settings_page(): void {
        echo '<div class="wrap">';
        echo '<h1>' . esc_html__('AIO Suite Settings', 'aio-suite') . '</h1>';
        echo '<div id="aio-settings-root">' . esc_html__('Loading settings…', 'aio-suite') . '</div>';
        echo '</div>';
    }

    public function enqueue_assets(string $hook): void {
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

    private function enqueue_admin_bundle(): void {
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

        wp_localize_script('aio-admin', 'AIO_SUITE_ENV', [
            'restUrl' => esc_url_raw(rest_url(self::REST_NAMESPACE)),
            'nonce' => wp_create_nonce('wp_rest'),
        ]);
    }

    private function enqueue_settings_bundle(): void {
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

        wp_localize_script('aio-settings', 'AIO_SUITE_ENV', [
            'restUrl' => esc_url_raw(rest_url(self::REST_NAMESPACE)),
            'nonce' => wp_create_nonce('wp_rest'),
        ]);
    }

    public function register_routes(): void {
        register_rest_route(
            self::REST_NAMESPACE,
            '/settings',
            [
                [
                    'methods' => WP_REST_Server::READABLE,
                    'callback' => [$this, 'rest_get_settings'],
                    'permission_callback' => [$this, 'can_manage_options'],
                ],
                [
                    'methods' => WP_REST_Server::EDITABLE,
                    'callback' => [$this, 'rest_update_settings'],
                    'permission_callback' => [$this, 'can_manage_options'],
                ],
            ]
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/generate',
            [
                'methods' => WP_REST_Server::CREATABLE,
                'callback' => [$this, 'rest_generate_article'],
                'permission_callback' => [$this, 'can_manage_options'],
            ]
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/history',
            [
                'methods' => WP_REST_Server::READABLE,
                'callback' => [$this, 'rest_history'],
                'permission_callback' => [$this, 'can_manage_options'],
            ]
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/history/(?P<history_id>[a-z0-9]+)',
            [
                'methods' => WP_REST_Server::READABLE,
                'callback' => [$this, 'rest_history_item'],
                'permission_callback' => [$this, 'can_manage_options'],
            ]
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/activity',
            [
                'methods' => WP_REST_Server::READABLE,
                'callback' => [$this, 'rest_activity'],
                'permission_callback' => [$this, 'can_manage_options'],
            ]
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/social',
            [
                'methods' => WP_REST_Server::CREATABLE,
                'callback' => [$this, 'rest_ingest_social'],
                'permission_callback' => '__return_true',
            ]
        );
    }

    public function can_manage_options(): bool {
        return current_user_can('manage_options');
    }

    private function get_settings(): array {
        $stored = get_option(self::OPTION_KEY, []);
        if (!is_array($stored)) {
            $stored = [];
        }

        $defaults = [
            'content_intel_url' => 'http://localhost:8000',
            'social_hub_url' => 'http://localhost:8080',
            'default_provider' => 'openai',
            'auto_publish' => false,
            'sites' => [],
            'encrypted_api_key' => '',
            'has_api_key' => false,
        ];

        $settings = wp_parse_args($stored, $defaults);
        $envKey = getenv('AIO_SUITE_PROVIDER_KEY');
        if ($envKey) {
            $settings['has_api_key'] = true;
        }

        return $settings;
    }

    private function save_settings(array $new_settings): void {
        $allowed = [
            'content_intel_url' => isset($new_settings['content_intel_url']) ? esc_url_raw($new_settings['content_intel_url']) : '',
            'social_hub_url' => isset($new_settings['social_hub_url']) ? esc_url_raw($new_settings['social_hub_url']) : '',
            'default_provider' => isset($new_settings['default_provider']) ? sanitize_text_field($new_settings['default_provider']) : 'openai',
            'auto_publish' => !empty($new_settings['auto_publish']),
            'sites' => array_map('esc_url_raw', $new_settings['sites'] ?? []),
        ];

        if (!empty($new_settings['encrypted_api_key'])) {
            $allowed['encrypted_api_key'] = $new_settings['encrypted_api_key'];
            $allowed['has_api_key'] = true;
        } elseif (isset($new_settings['has_api_key']) && !$new_settings['has_api_key']) {
            $allowed['encrypted_api_key'] = '';
            $allowed['has_api_key'] = false;
        }

        update_option(self::OPTION_KEY, $allowed, false);
    }

    private function get_encryption_key(): string {
        $seed = getenv('AIO_SUITE_ENC_KEY');
        if (!$seed) {
            $seed = wp_salt('auth');
        }
        return substr(hash('sha256', $seed, true), 0, 32);
    }

    private function encrypt(string $value): string {
        $key = $this->get_encryption_key();
        $iv = random_bytes(16);
        $cipher = openssl_encrypt($value, 'aes-256-cbc', $key, OPENSSL_RAW_DATA, $iv);
        return base64_encode($iv . $cipher);
    }

    private function decrypt(string $payload): string {
        $key = $this->get_encryption_key();
        $data = base64_decode($payload, true);
        if (!$data || strlen($data) <= 16) {
            return '';
        }
        $iv = substr($data, 0, 16);
        $cipher = substr($data, 16);
        $plain = openssl_decrypt($cipher, 'aes-256-cbc', $key, OPENSSL_RAW_DATA, $iv);
        return $plain ?: '';
    }

    private function get_provider_key(): string {
        $env = getenv('AIO_SUITE_PROVIDER_KEY');
        if ($env) {
            return $env;
        }
        $settings = $this->get_settings();
        if (!empty($settings['encrypted_api_key'])) {
            return $this->decrypt($settings['encrypted_api_key']);
        }
        return '';
    }

    public function rest_get_settings(): WP_REST_Response {
        $settings = $this->get_settings();
        $response = [
            'content_intel_url' => $settings['content_intel_url'],
            'social_hub_url' => $settings['social_hub_url'],
            'default_provider' => $settings['default_provider'],
            'auto_publish' => (bool) $settings['auto_publish'],
            'sites' => $settings['sites'],
            'has_api_key' => (bool) $settings['has_api_key'] || (bool) getenv('AIO_SUITE_PROVIDER_KEY'),
        ];
        return new WP_REST_Response($response, 200);
    }

    public function rest_update_settings(WP_REST_Request $request) {
        $body = $request->get_json_params();
        $settings = $this->get_settings();

        $settings['content_intel_url'] = esc_url_raw($body['content_intel_url'] ?? $settings['content_intel_url']);
        $settings['social_hub_url'] = esc_url_raw($body['social_hub_url'] ?? $settings['social_hub_url']);
        $settings['default_provider'] = sanitize_text_field($body['default_provider'] ?? $settings['default_provider']);
        $settings['auto_publish'] = !empty($body['auto_publish']);
        $settings['sites'] = array_map('esc_url_raw', $body['sites'] ?? $settings['sites']);

        if (!empty($body['api_key'])) {
            $settings['encrypted_api_key'] = $this->encrypt(sanitize_text_field($body['api_key']));
            $settings['has_api_key'] = true;
        }

        if (isset($body['clear_api_key']) && $body['clear_api_key']) {
            $settings['encrypted_api_key'] = '';
            $settings['has_api_key'] = false;
        }

        $this->save_settings($settings);
        return $this->rest_get_settings();
    }

    private function build_service_url(string $path): string {
        $settings = $this->get_settings();
        return trailingslashit($settings['content_intel_url']) . ltrim($path, '/');
    }

    public function rest_generate_article(WP_REST_Request $request) {
        $params = $request->get_json_params();
        $payload = [
            'keyword' => sanitize_text_field($params['keyword'] ?? ''),
            'geo' => sanitize_text_field($params['geo'] ?? 'ID'),
            'tone' => sanitize_text_field($params['tone'] ?? 'neutral'),
            'target_language' => sanitize_text_field($params['target_language'] ?? 'id'),
            'min_words' => max(500, intval($params['min_words'] ?? 800)),
            'max_words' => max(600, intval($params['max_words'] ?? 1600)),
            'include_images' => !empty($params['include_images']),
            'include_social_summary' => !empty($params['include_social_summary']),
            'additional_context' => sanitize_textarea_field($params['additional_context'] ?? ''),
            'sitemap_url' => esc_url_raw($params['sitemap_url'] ?? ''),
            'site_url' => esc_url_raw(home_url()),
            'secondary_keywords' => array_map('sanitize_text_field', $params['secondary_keywords'] ?? []),
            'custom_reference_urls' => array_map('esc_url_raw', $params['custom_reference_urls'] ?? []),
            'auto_publish' => !empty($params['auto_publish']),
            'schedule_at' => sanitize_text_field($params['schedule_at'] ?? ''),
        ];

        if (empty($payload['keyword'])) {
            return new WP_Error('aio_missing_keyword', __('Keyword is required.', 'aio-suite'), ['status' => 400]);
        }

        $response = wp_remote_post(
            $this->build_service_url('/api/content/generate_article'),
            [
                'headers' => $this->service_headers(),
                'body' => wp_json_encode($payload),
                'timeout' => 60,
            ]
        );

        return $this->format_service_response($response);
    }

    public function rest_history(WP_REST_Request $request) {
        $limit = max(1, min(50, intval($request->get_param('limit') ?? 10)));
        $response = wp_remote_get(
            add_query_arg('limit', $limit, $this->build_service_url('/api/content/history')),
            ['headers' => $this->service_headers(), 'timeout' => 30]
        );
        return $this->format_service_response($response);
    }

    public function rest_history_item(WP_REST_Request $request) {
        $history_id = sanitize_text_field($request->get_param('history_id'));
        if (!$history_id) {
            return new WP_Error('aio_missing_history_id', __('History ID required.', 'aio-suite'), ['status' => 400]);
        }
        $response = wp_remote_get(
            $this->build_service_url('/api/content/history/' . rawurlencode($history_id)),
            ['headers' => $this->service_headers(), 'timeout' => 30]
        );
        return $this->format_service_response($response);
    }

    public function rest_activity(WP_REST_Request $request) {
        $limit = max(1, min(100, intval($request->get_param('limit') ?? 25)));
        $response = wp_remote_get(
            add_query_arg('limit', $limit, $this->build_service_url('/api/content/activity')),
            ['headers' => $this->service_headers(), 'timeout' => 30]
        );
        return $this->format_service_response($response);
    }

    public function rest_ingest_social(WP_REST_Request $request) {
        $token = $request->get_header('x-aio-token');
        $expected = getenv('AIO_SUITE_SOCIAL_TOKEN');
        if (!$expected || !hash_equals($expected, (string) $token)) {
            return new WP_Error('aio_forbidden', __('Invalid social ingestion token.', 'aio-suite'), ['status' => 403]);
        }

        $body = $request->get_json_params();
        $title = sanitize_text_field($body['title'] ?? 'Social Update');
        $caption = wp_kses_post($body['caption'] ?? '');
        $url = esc_url_raw($body['url'] ?? '');

        $post_id = wp_insert_post([
            'post_title' => $title,
            'post_content' => $caption . ($url ? '<p><a href="' . esc_url($url) . '">' . esc_html__('Baca selengkapnya', 'aio-suite') . '</a></p>' : ''),
            'post_status' => 'draft',
            'post_type' => 'post',
            'meta_input' => [
                '_aio_suite_social_source' => 'hub',
                '_aio_suite_social_url' => $url,
            ],
        ], true);

        if (is_wp_error($post_id)) {
            return $post_id;
        }

        return new WP_REST_Response([
            'status' => 'queued',
            'post_id' => $post_id,
        ], 200);
    }

    private function service_headers(): array {
        $headers = ['Content-Type' => 'application/json'];
        $key = $this->get_provider_key();
        if ($key) {
            $headers['X-AIO-Provider-Key'] = $key;
        }
        return $headers;
    }

    private function format_service_response($response) {
        if (is_wp_error($response)) {
            return new WP_Error('aio_service_error', $response->get_error_message(), ['status' => 502]);
        }

        $code = wp_remote_retrieve_response_code($response);
        $body = wp_remote_retrieve_body($response);
        $decoded = json_decode($body, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            $decoded = ['raw' => $body];
        }
        return new WP_REST_Response($decoded, $code ?: 200);
    }
}

register_activation_hook(__FILE__, ['AIO_Content_Suite', 'activate']);
new AIO_Content_Suite();

