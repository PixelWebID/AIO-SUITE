<?php
/**
 * Plugin Name: AIO Content Suite
 * Description: Agent WP bridge for the AIO Suite. Generates articles, analyses gaps, schedules social posts, and manages history inside WordPress.
 * Version: 1.0.0
 * Author: AIO Team
 */

if (! defined('ABSPATH')) {
    exit;
}

final class AIO_Content_Suite
{
    private const VERSION = '1.0.0';
    private const OPTION_KEY = 'aio_suite_settings';
    private const API_KEY_OPTION = 'aio_suite_api_keys';
    private const REST_NAMESPACE = 'aio/v1';

    private static ?self $instance = null;

    public static function bootstrap(): void
    {
        if (self::$instance instanceof self) {
            return;
        }

        self::$instance = new self();
        add_action('admin_menu', [self::$instance, 'register_menus']);
        add_action('network_admin_menu', [self::$instance, 'register_network_menu']);
        add_action('admin_enqueue_scripts', [self::$instance, 'enqueue_assets']);
        add_action('rest_api_init', [self::$instance, 'register_rest_routes']);
    }

    public static function activate(): void
    {
        global $wpdb;
        require_once ABSPATH . 'wp-admin/includes/upgrade.php';

        $charset = $wpdb->get_charset_collate();
        $articles = $wpdb->prefix . 'aio_articles';
        $refs = $wpdb->prefix . 'aio_refs';
        $logs = $wpdb->prefix . 'aio_logs';
        $sites = $wpdb->prefix . 'aio_sites';
        $groups = $wpdb->prefix . 'aio_keyword_groups';
        $relations = $wpdb->prefix . 'aio_article_relations';

        $queries = [
            "CREATE TABLE {$articles} (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                history_id VARCHAR(64) NOT NULL,
                keyword VARCHAR(255) NOT NULL,
                geo VARCHAR(8) DEFAULT 'ID',
                tone VARCHAR(32) DEFAULT 'neutral',
                status VARCHAR(32) DEFAULT 'draft',
                article_html LONGTEXT,
                meta_json LONGTEXT,
                metrics_json LONGTEXT,
                warnings_json LONGTEXT,
                internal_links_json LONGTEXT,
                images_json LONGTEXT,
                draft_payload LONGTEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                scheduled_for DATETIME NULL,
                published_post_id BIGINT UNSIGNED NULL,
                PRIMARY KEY (id),
                KEY history_id (history_id),
                KEY status (status),
                KEY created_at (created_at)
            ) {$charset};",
            "CREATE TABLE {$refs} (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                article_id BIGINT UNSIGNED NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                snippet TEXT NULL,
                domain VARCHAR(255) NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY article_id (article_id)
            ) {$charset};",
            "CREATE TABLE {$logs} (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                article_id BIGINT UNSIGNED NULL,
                level VARCHAR(16) DEFAULT 'info',
                context VARCHAR(64) NOT NULL,
                message TEXT,
                payload_json LONGTEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY context (context),
                KEY article_id (article_id)
            ) {$charset};",
            "CREATE TABLE {$sites} (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                domain VARCHAR(255) NOT NULL,
                token VARCHAR(255) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY domain (domain)
            ) {$charset};",
            "CREATE TABLE {$groups} (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                group_name VARCHAR(190) NOT NULL,
                keywords_json LONGTEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE KEY group_name (group_name)
            ) {$charset};",
            "CREATE TABLE {$relations} (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                parent_article_id BIGINT UNSIGNED NOT NULL,
                child_article_id BIGINT UNSIGNED NOT NULL,
                relation_type VARCHAR(32) DEFAULT 'child',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                KEY parent_article_id (parent_article_id),
                KEY child_article_id (child_article_id)
            ) {$charset};",
        ];

        foreach ($queries as $sql) {
            dbDelta($sql);
        }
    }

    public function register_menus(): void
    {
        add_menu_page(
            __('AIO Suite', 'aio-suite'),
            __('AIO Suite', 'aio-suite'),
            'edit_posts',
            'aio-suite',
            [$this, 'render_dashboard'],
            'dashicons-analytics',
            58
        );

        add_submenu_page(
            'aio-suite',
            __('Dashboard', 'aio-suite'),
            __('Dashboard', 'aio-suite'),
            'edit_posts',
            'aio-suite',
            [$this, 'render_dashboard']
        );

        add_submenu_page(
            'aio-suite',
            __('Settings', 'aio-suite'),
            __('Settings', 'aio-suite'),
            'manage_options',
            'aio-suite-settings',
            [$this, 'render_settings']
        );

        add_submenu_page(
            'aio-suite',
            __('History', 'aio-suite'),
            __('History', 'aio-suite'),
            'edit_posts',
            'aio-suite-history',
            [$this, 'render_history']
        );
    }
    public function register_network_menu(): void
    {
        if (! is_multisite()) {
            return;
        }

        add_menu_page(
            __('AIO Suite Network', 'aio-suite'),
            __('AIO Suite', 'aio-suite'),
            'manage_network_options',
            'aio-suite-network',
            [$this, 'render_settings'],
            'dashicons-analytics'
        );
    }

    public function enqueue_assets(string $hook): void
    {
        $screen = get_current_screen();
        if (! $screen) {
            return;
        }

        $is_dashboard = in_array($screen->id, ['toplevel_page_aio-suite', 'aio-suite_page_aio-suite-history'], true);
        $is_settings = in_array($screen->id, ['aio-suite_page_aio-suite-settings', 'aio-suite-network'], true);

        if ($is_dashboard) {
            wp_enqueue_script(
                'aio-suite-admin',
                plugin_dir_url(__FILE__) . 'src/admin.js',
                [],
                self::VERSION,
                true
            );
            wp_enqueue_style(
                'aio-suite-style',
                plugin_dir_url(__FILE__) . 'src/style.css',
                [],
                self::VERSION
            );
            wp_localize_script(
                'aio-suite-admin',
                'AIO_SUITE_ENV',
                $this->localize_env($screen->id === 'aio-suite_page_aio-suite-history' ? 'history' : 'dashboard')
            );
        }

        if ($is_settings) {
            wp_enqueue_script(
                'aio-suite-settings',
                plugin_dir_url(__FILE__) . 'src/settings.js',
                [],
                self::VERSION,
                true
            );
            wp_enqueue_style(
                'aio-suite-style',
                plugin_dir_url(__FILE__) . 'src/style.css',
                [],
                self::VERSION
            );
            wp_localize_script(
                'aio-suite-settings',
                'AIO_SUITE_ENV',
                $this->localize_env('settings')
            );
        }
    }

    public function render_dashboard(): void
    {
        echo '<div class="wrap aio-suite-wrap">';
        echo '<h1>' . esc_html__('AIO Suite Dashboard', 'aio-suite') . '</h1>';
        echo '<div id="aio-root" data-screen="dashboard">' . esc_html__('Loading interface…', 'aio-suite') . '</div>';
        echo '</div>';
    }

    public function render_settings(): void
    {
        echo '<div class="wrap aio-suite-wrap">';
        echo '<h1>' . esc_html__('AIO Suite Settings', 'aio-suite') . '</h1>';
        echo '<div id="aio-settings-root" data-screen="settings">' . esc_html__('Loading settings…', 'aio-suite') . '</div>';
        echo '</div>';
    }

    public function render_history(): void
    {
        echo '<div class="wrap aio-suite-wrap">';
        echo '<h1>' . esc_html__('AIO Suite History', 'aio-suite') . '</h1>';
        echo '<div id="aio-root" data-screen="history">' . esc_html__('Loading history…', 'aio-suite') . '</div>';
        echo '</div>';
    }

    public function register_rest_routes(): void
    {
        register_rest_route(
            self::REST_NAMESPACE,
            '/generate',
            [
                'methods' => 'POST',
                'callback' => [$this, 'rest_generate_article'],
                'permission_callback' => fn () => $this->verify_request_capability('edit_posts'),
            ]
        );
        register_rest_route(
            self::REST_NAMESPACE,
            '/generate_rss',
            [
                'methods' => 'POST',
                'callback' => [$this, 'rest_generate_rss'],
                'permission_callback' => fn () => $this->verify_request_capability('edit_posts'),
            ]
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/gap',
            [
                'methods' => 'GET',
                'callback' => [$this, 'rest_gap_analysis'],
                'permission_callback' => fn () => $this->verify_request_capability('edit_posts'),
            ]
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/publish',
            [
                'methods' => 'POST',
                'callback' => [$this, 'rest_publish_article'],
                'permission_callback' => fn () => $this->verify_request_capability('publish_posts'),
            ]
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/history',
            [
                'methods' => 'GET',
                'callback' => [$this, 'rest_history'],
                'permission_callback' => fn () => $this->verify_request_capability('edit_posts'),
            ]
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/history/(?P<id>\d+)',
            [
                'methods' => 'GET',
                'callback' => [$this, 'rest_history_item'],
                'permission_callback' => fn () => $this->verify_request_capability('edit_posts'),
            ]
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/settings',
            [
                [
                    'methods' => 'GET',
                    'callback' => [$this, 'rest_get_settings'],
                    'permission_callback' => fn () => $this->verify_request_capability('manage_options'),
                ],
                [
                    'methods' => 'POST',
                    'callback' => [$this, 'rest_update_settings'],
                    'permission_callback' => fn () => $this->verify_request_capability('manage_options'),
                ],
            ]
        );

        register_rest_route(
            self::REST_NAMESPACE,
            '/settings/validate',
            [
                'methods' => 'POST',
                'callback' => [$this, 'rest_validate_settings'],
                'permission_callback' => fn () => $this->verify_request_capability('manage_options'),
            ]
        );
    }
    public function rest_generate_article(WP_REST_Request $request)
    {
        $payload = $this->sanitize_article_request($request->get_json_params());
        if (empty($payload['keyword'])) {
            return new WP_Error('aio_missing_keyword', __('Keyword is required.', 'aio-suite'), ['status' => 400]);
        }

        $response = $this->proxy_content_intel('/api/content/generate_article', $payload);
        if (is_wp_error($response)) {
            return $response;
        }

        $body = $this->decode_response_body($response);
        $record = $this->save_draft_article($payload, $body);

        return new WP_REST_Response([
            'article' => $body,
            'record' => $record,
        ], wp_remote_retrieve_response_code($response) ?: 200);
    }

    public function rest_generate_rss(WP_REST_Request $request)
    {
        $payload = $request->get_json_params();
        if (empty($payload['feed_url'])) {
            return new WP_Error('aio_missing_feed', __('Feed URL is required.', 'aio-suite'), ['status' => 400]);
        }

        $response = $this->proxy_content_intel('/api/content/generate_from_rss', $payload);
        if (is_wp_error($response)) {
            return $response;
        }

        $body = $this->decode_response_body($response);
        $record = $this->save_draft_article([
            'keyword' => sanitize_text_field($payload['keyword'] ?? ($body['meta']['title'] ?? '')),
            'geo' => sanitize_text_field($payload['geo'] ?? 'ID'),
            'tone' => sanitize_text_field($payload['tone'] ?? 'neutral'),
        ], $body);

        return new WP_REST_Response([
            'article' => $body,
            'record' => $record,
        ], wp_remote_retrieve_response_code($response) ?: 200);
    }
    public function rest_gap_analysis(WP_REST_Request $request)
    {
        $keyword = sanitize_text_field($request->get_param('keyword'));
        if (! $keyword) {
            return new WP_Error('aio_missing_keyword', __('Keyword is required.', 'aio-suite'), ['status' => 400]);
        }

        $payload = [
            'keyword' => $keyword,
            'geo' => sanitize_text_field($request->get_param('geo') ?? 'ID'),
        ];

        $competitors = $request->get_param('competitors');
        if (is_array($competitors)) {
            $payload['competitors'] = array_map('esc_url_raw', $competitors);
        }

        $response = $this->proxy_content_intel('/api/analysis/content_gap', $payload, 'GET');
        if (is_wp_error($response)) {
            return $response;
        }

        return new WP_REST_Response($this->decode_response_body($response), wp_remote_retrieve_response_code($response) ?: 200);
    }

    public function rest_publish_article(WP_REST_Request $request)
    {
        $payload = $request->get_json_params();
        $article = $payload['article'] ?? [];
        $meta = $article['meta'] ?? [];
        $article_html = $article['article_html'] ?? '';

        if (! $article_html) {
            return new WP_Error('aio_missing_article', __('Article payload missing.', 'aio-suite'), ['status' => 400]);
        }

        $record_id = intval($payload['record_id'] ?? 0) ?: null;
        $schedule_at = ! empty($payload['schedule_at']) ? sanitize_text_field($payload['schedule_at']) : null;
        $images = is_array($article['images'] ?? null) ? $article['images'] : [];

        $post = $this->publish_article($article_html, $meta, $images, $schedule_at);
        if (is_wp_error($post)) {
            return $post;
        }

        if ($record_id) {
            $this->update_history($record_id, [
                'status' => $schedule_at ? 'scheduled' : 'published',
                'published_post_id' => $post['post_id'],
                'scheduled_for' => $schedule_at,
            ]);
        }

        $social_result = null;
        if (! empty($payload['social']['networks'])) {
            $social_payload = [
                'title' => $meta['title'] ?? get_the_title($post['post_id']),
                'url' => get_permalink($post['post_id']),
                'summary' => $meta['description'] ?? '',
                'networks' => array_map('sanitize_text_field', (array) $payload['social']['networks']),
                'tone' => sanitize_text_field($payload['social']['tone'] ?? 'casual'),
                'scheduleAt' => $schedule_at,
            ];
            $response = $this->proxy_social_hub('/api/publish', $social_payload);
            if (is_wp_error($response)) {
                $this->log_event($record_id, 'error', 'social_publish_failed', $response->get_error_message(), $social_payload);
            } else {
                $social_result = $this->decode_response_body($response);
            }
        }

        return new WP_REST_Response([
            'post' => $post,
            'social' => $social_result,
        ], 200);
    }
    public function rest_history(WP_REST_Request $request)
    {
        global $wpdb;
        $limit = max(1, min(100, intval($request->get_param('limit') ?? 20)));
        $status = sanitize_text_field($request->get_param('status') ?? '');
        $date_from = sanitize_text_field($request->get_param('date_from') ?? '');
        $date_to = sanitize_text_field($request->get_param('date_to') ?? '');

        $clauses = ['1=1'];
        $args = [];

        if ($status) {
            $clauses[] = 'status = %s';
            $args[] = $status;
        }
        if ($date_from) {
            $clauses[] = 'created_at >= %s';
            $args[] = $date_from;
        }
        if ($date_to) {
            $clauses[] = 'created_at <= %s';
            $args[] = $date_to;
        }

        $sql = 'SELECT * FROM ' . $wpdb->prefix . 'aio_articles WHERE ' . implode(' AND ', $clauses) . ' ORDER BY created_at DESC LIMIT %d';
        $args[] = $limit;

        $rows = $wpdb->get_results($wpdb->prepare($sql, $args), ARRAY_A);
        $history = array_map([$this, 'format_article_row'], $rows);

        return new WP_REST_Response(['history' => $history], 200);
    }

    public function rest_history_item(WP_REST_Request $request)
    {
        global $wpdb;
        $id = intval($request->get_param('id'));
        if ($id <= 0) {
            return new WP_Error('aio_history_invalid', __('Invalid history id.', 'aio-suite'), ['status' => 400]);
        }

        $row = $wpdb->get_row($wpdb->prepare('SELECT * FROM ' . $wpdb->prefix . 'aio_articles WHERE id = %d', $id), ARRAY_A);
        if (! $row) {
            return new WP_Error('aio_history_missing', __('History item not found.', 'aio-suite'), ['status' => 404]);
        }

        $refs = $wpdb->get_results($wpdb->prepare('SELECT * FROM ' . $wpdb->prefix . 'aio_refs WHERE article_id = %d', $id), ARRAY_A);

        return new WP_REST_Response([
            'record' => $this->format_article_row($row),
            'references' => $refs,
        ], 200);
    }

    public function rest_get_settings(): WP_REST_Response
    {
        return new WP_REST_Response($this->get_settings(), 200);
    }

    public function rest_update_settings(WP_REST_Request $request)
    {
        global $wpdb;
        $params = $request->get_json_params();
        $settings = $this->get_settings();

        $settings['content_intel_url'] = esc_url_raw($params['content_intel_url'] ?? $settings['content_intel_url']);
        $settings['social_hub_url'] = esc_url_raw($params['social_hub_url'] ?? $settings['social_hub_url']);
        $mode = $params['api_mode'] ?? $settings['api_mode'];
        $settings['api_mode'] = in_array($mode, ['backend', 'wp'], true) ? $mode : 'backend';
        $settings['fallback_order'] = array_values(array_filter(array_map('sanitize_text_field', $params['fallback_order'] ?? $settings['fallback_order'])));
        $settings['auto_publish'] = ! empty($params['auto_publish']);
        $settings['auto_regenerate'] = ! empty($params['auto_regenerate']);
        $settings['default_tone'] = sanitize_text_field($params['default_tone'] ?? $settings['default_tone']);
        $settings['default_language'] = sanitize_text_field($params['default_language'] ?? $settings['default_language']);
        $settings['default_geo'] = sanitize_text_field($params['default_geo'] ?? $settings['default_geo'] ?? 'ID');

        $settings['sites'] = [];
        $wpdb->query('TRUNCATE TABLE ' . $wpdb->prefix . 'aio_sites');
        if (! empty($params['sites']) && is_array($params['sites'])) {
            foreach ($params['sites'] as $site) {
                $domain = esc_url_raw($site['domain'] ?? '');
                $token = sanitize_text_field($site['token'] ?? '');
                if ($domain && $token) {
                    $settings['sites'][] = [
                        'domain' => $domain,
                        'token' => $token,
                    ];
                    $wpdb->insert($wpdb->prefix . 'aio_sites', [
                        'domain' => $domain,
                        'token' => $token,
                        'created_at' => current_time('mysql'),
                        'updated_at' => current_time('mysql'),
                    ]);
                }
            }
        }

        update_option(self::OPTION_KEY, $settings, false);

        if ($settings['api_mode'] === 'wp' && ! empty($params['keys'])) {
            $keys = $params['keys'];
            $payload = [
                'openai' => sanitize_text_field($keys['openai'] ?? ''),
                'deepseek' => sanitize_text_field($keys['deepseek'] ?? ''),
                'openrouter' => sanitize_text_field($keys['openrouter'] ?? ''),
                'gemini' => sanitize_text_field($keys['gemini'] ?? ''),
                'llama' => sanitize_text_field($keys['llama'] ?? ''),
                'pexels' => sanitize_text_field($keys['pexels'] ?? ''),
                'pixabay' => sanitize_text_field($keys['pixabay'] ?? ''),
                'trends_username' => sanitize_text_field($keys['trends_username'] ?? ''),
                'trends_password' => sanitize_text_field($keys['trends_password'] ?? ''),
            ];
            update_option(self::API_KEY_OPTION, $this->encrypt(wp_json_encode($payload)), false);
        } elseif ($settings['api_mode'] !== 'wp') {
            delete_option(self::API_KEY_OPTION);
        }

        return new WP_REST_Response($this->get_settings(), 200);
    }

    public function rest_validate_settings(WP_REST_Request $request)
    {
        $params = $request->get_json_params();
        $content_intel_url = esc_url_raw($params['content_intel_url'] ?? '');
        $social_hub_url = esc_url_raw($params['social_hub_url'] ?? '');

        $results = [];
        if ($content_intel_url) {
            $response = wp_remote_get(trailingslashit($content_intel_url) . 'health', ['timeout' => 10]);
            $results['content_intel'] = is_wp_error($response)
                ? ['ok' => false, 'detail' => $response->get_error_message()]
                : ['ok' => wp_remote_retrieve_response_code($response) === 200, 'detail' => wp_remote_retrieve_body($response)];
        }

        if ($social_hub_url) {
            $response = wp_remote_get(trailingslashit($social_hub_url) . 'health', ['timeout' => 10]);
            $results['social_hub'] = is_wp_error($response)
                ? ['ok' => false, 'detail' => $response->get_error_message()]
                : ['ok' => wp_remote_retrieve_response_code($response) === 200, 'detail' => wp_remote_retrieve_body($response)];
        }

        return new WP_REST_Response($results, 200);
    }
    private function sanitize_article_request(array $payload): array
    {
        return [
            'keyword' => sanitize_text_field($payload['keyword'] ?? ''),
            'geo' => sanitize_text_field($payload['geo'] ?? 'ID'),
            'tone' => sanitize_text_field($payload['tone'] ?? 'neutral'),
            'target_language' => sanitize_text_field($payload['target_language'] ?? 'id'),
            'min_words' => max(300, intval($payload['min_words'] ?? 800)),
            'max_words' => max(600, intval($payload['max_words'] ?? 1600)),
            'max_references' => max(3, intval($payload['max_references'] ?? 7)),
            'include_images' => ! empty($payload['include_images']),
            'include_social_summary' => ! empty($payload['include_social_summary']),
            'additional_context' => sanitize_textarea_field($payload['additional_context'] ?? ''),
            'sitemap_url' => esc_url_raw($payload['sitemap_url'] ?? ''),
            'site_url' => esc_url_raw(home_url()),
            'secondary_keywords' => array_map('sanitize_text_field', $payload['secondary_keywords'] ?? []),
            'custom_reference_urls' => array_map('esc_url_raw', $payload['custom_reference_urls'] ?? []),
            'image_provider_preference' => sanitize_text_field($payload['image_provider_preference'] ?? 'auto'),
            'llm_provider_priority' => array_map('sanitize_text_field', $payload['llm_provider_priority'] ?? $this->get_settings()['fallback_order']),
        ];
    }

    private function proxy_content_intel(string $path, array $payload = [], string $method = 'POST')
    {
        $settings = $this->get_settings();
        $endpoint = trailingslashit($settings['content_intel_url']) . ltrim($path, '/');
        $headers = ['Content-Type' => 'application/json'];
        $provider_key = $this->resolve_provider_key();
        if ($provider_key) {
            $headers['X-AIO-Provider-Key'] = $provider_key;
        }

        if ($method === 'GET') {
            $endpoint = add_query_arg($payload, $endpoint);
            return wp_remote_get($endpoint, ['timeout' => 60, 'headers' => $headers]);
        }

        return wp_remote_post($endpoint, [
            'timeout' => 60,
            'body' => wp_json_encode($payload),
            'headers' => $headers,
        ]);
    }

    private function proxy_social_hub(string $path, array $payload)
    {
        $settings = $this->get_settings();
        $endpoint = trailingslashit($settings['social_hub_url']) . ltrim($path, '/');
        return wp_remote_post($endpoint, [
            'timeout' => 45,
            'body' => wp_json_encode($payload),
            'headers' => ['Content-Type' => 'application/json'],
        ]);
    }

    private function decode_response_body($response): array
    {
        $body = wp_remote_retrieve_body($response);
        $decoded = json_decode($body, true);
        return json_last_error() === JSON_ERROR_NONE ? $decoded : ['raw' => $body];
    }
    private function save_draft_article(array $payload, array $response): array
    {
        global $wpdb;
        $history_id = sanitize_text_field($response['history_id'] ?? wp_generate_password(20, false));
        $meta = $response['meta'] ?? [];
        $metrics = $response['metrics'] ?? [];
        $warnings = $response['warnings'] ?? [];
        $sources = $response['sources'] ?? [];
        $images = $response['images'] ?? [];

        $internal_links = [];
        if (! empty($payload['sitemap_url'])) {
            $internal_links = $this->internal_linking_from_sitemap($payload['sitemap_url'], $response['article_html'] ?? '');
        }

        $wpdb->insert($wpdb->prefix . 'aio_articles', [
            'history_id' => $history_id,
            'keyword' => $payload['keyword'],
            'geo' => $payload['geo'],
            'tone' => $payload['tone'],
            'status' => 'draft',
            'article_html' => $response['article_html'] ?? '',
            'meta_json' => wp_json_encode($meta),
            'metrics_json' => wp_json_encode($metrics),
            'warnings_json' => wp_json_encode($warnings),
            'internal_links_json' => wp_json_encode($internal_links),
            'images_json' => wp_json_encode($images),
            'draft_payload' => wp_json_encode($payload),
            'created_at' => current_time('mysql'),
        ]);
        $article_id = intval($wpdb->insert_id);

        if ($article_id && is_array($sources)) {
            foreach ($sources as $source) {
                $wpdb->insert($wpdb->prefix . 'aio_refs', [
                    'article_id' => $article_id,
                    'title' => sanitize_text_field($source['title'] ?? ''),
                    'url' => esc_url_raw($source['url'] ?? ''),
                    'snippet' => sanitize_textarea_field($source['snippet'] ?? ''),
                    'domain' => sanitize_text_field($source['domain'] ?? ''),
                    'created_at' => current_time('mysql'),
                ]);
            }
        }

        $this->log_event($article_id, 'info', 'article_draft_saved', 'Draft stored locally.', [
            'keyword' => $payload['keyword'],
            'history_id' => $history_id,
        ]);

        $row = $wpdb->get_row($wpdb->prepare('SELECT * FROM ' . $wpdb->prefix . 'aio_articles WHERE id = %d', $article_id), ARRAY_A);
        return $this->format_article_row($row);
    }

    private function publish_article(string $article_html, array $meta, array $images, ?string $schedule): array
    {
        $status = $schedule ? 'future' : 'publish';
        $postarr = [
            'post_title' => sanitize_text_field($meta['title'] ?? __('AIO Draft', 'aio-suite')),
            'post_content' => wp_kses_post($article_html),
            'post_status' => $status,
            'post_type' => 'post',
        ];

        if ($schedule) {
            $postarr['post_date'] = gmdate('Y-m-d H:i:s', strtotime($schedule));
        }

        $post_id = wp_insert_post($postarr, true);
        if (is_wp_error($post_id)) {
            return $post_id;
        }

        if (! empty($images)) {
            $this->set_featured_image($post_id, $images[0]['url'] ?? '');
        }

        if (! empty($meta['tags'])) {
            wp_set_post_tags($post_id, $meta['tags']);
        }

        if (! empty($meta['categories'])) {
            $category_ids = [];
            foreach ((array) $meta['categories'] as $category) {
                $term = get_term_by('name', $category, 'category');
                if (! $term) {
                    $term = wp_insert_term($category, 'category');
                }
                if (! is_wp_error($term)) {
                    $category_ids[] = intval($term['term_id']);
                }
            }
            if ($category_ids) {
                wp_set_post_categories($post_id, $category_ids);
            }
        }

        if (! empty($meta['description'])) {
            update_post_meta($post_id, '_aio_meta_description', sanitize_text_field($meta['description']));
        }

        return [
            'post_id' => $post_id,
            'status' => $status,
            'scheduled_for' => $schedule,
        ];
    }

    private function update_history(int $article_id, array $fields): void
    {
        global $wpdb;
        $wpdb->update($wpdb->prefix . 'aio_articles', $fields, ['id' => $article_id]);
    }

    private function internal_linking_from_sitemap(string $sitemap_url, string $article_html): array
    {
        if (! $sitemap_url) {
            return [];
        }

        $response = wp_remote_get($sitemap_url, ['timeout' => 20]);
        if (is_wp_error($response)) {
            return [];
        }

        $body = wp_remote_retrieve_body($response);
        if (! $body) {
            return [];
        }

        $xml = simplexml_load_string($body);
        if (! $xml) {
            return [];
        }

        $links = [];
        foreach ($xml->url as $node) {
            $loc = (string) ($node->loc ?? '');
            if (! $loc) {
                continue;
            }
            $slug = basename(untrailingslashit($loc));
            if (stripos($article_html, $slug) !== false) {
                $links[] = [
                    'anchor' => ucwords(str_replace('-', ' ', $slug)),
                    'url' => esc_url_raw($loc),
                ];
            }
            if (count($links) >= 10) {
                break;
            }
        }

        return $links;
    }

    private function set_featured_image(int $post_id, string $image_url): void
    {
        if (! $image_url) {
            return;
        }

        require_once ABSPATH . 'wp-admin/includes/media.php';
        require_once ABSPATH . 'wp-admin/includes/file.php';
        require_once ABSPATH . 'wp-admin/includes/image.php';

        $attachment_id = media_sideload_image($image_url, $post_id, null, 'id');
        if (! is_wp_error($attachment_id)) {
            set_post_thumbnail($post_id, $attachment_id);
        }
    }

    private function log_event(?int $article_id, string $level, string $context, string $message, array $payload = []): void
    {
        global $wpdb;
        $wpdb->insert($wpdb->prefix . 'aio_logs', [
            'article_id' => $article_id,
            'level' => sanitize_text_field($level),
            'context' => sanitize_text_field($context),
            'message' => sanitize_text_field($message),
            'payload_json' => wp_json_encode($payload),
            'created_at' => current_time('mysql'),
        ]);
    }

    private function format_article_row(?array $row): array
    {
        if (! $row) {
            return [];
        }

        return [
            'id' => intval($row['id']),
            'history_id' => $row['history_id'],
            'keyword' => $row['keyword'],
            'geo' => $row['geo'],
            'tone' => $row['tone'],
            'status' => $row['status'],
            'article_html' => $row['article_html'],
            'meta' => json_decode($row['meta_json'] ?? '[]', true) ?: [],
            'metrics' => json_decode($row['metrics_json'] ?? '[]', true) ?: [],
            'warnings' => json_decode($row['warnings_json'] ?? '[]', true) ?: [],
            'internal_links' => json_decode($row['internal_links_json'] ?? '[]', true) ?: [],
            'images' => json_decode($row['images_json'] ?? '[]', true) ?: [],
            'created_at' => $row['created_at'],
            'updated_at' => $row['updated_at'],
            'scheduled_for' => $row['scheduled_for'],
            'published_post_id' => $row['published_post_id'],
        ];
    }

    private function verify_request_capability(string $capability): bool
    {
        if (! current_user_can($capability)) {
            return false;
        }
        $nonce = $_SERVER['HTTP_X_WP_NONCE'] ?? '';
        return $nonce && wp_verify_nonce($nonce, 'wp_rest');
    }

    private function localize_env(string $screen): array
    {
        return [
            'version' => self::VERSION,
            'restUrl' => esc_url_raw(rest_url(self::REST_NAMESPACE)),
            'nonce' => wp_create_nonce('wp_rest'),
            'screen' => $screen,
            'settings' => $this->get_settings(),
        ];
    }

    private function get_settings(): array
    {
        $defaults = [
            'content_intel_url' => 'http://localhost:8000',
            'social_hub_url' => 'http://localhost:8080',
            'api_mode' => 'backend',
            'fallback_order' => ['openai', 'deepseek', 'openrouter', 'gemini', 'llama'],
            'auto_publish' => false,
            'auto_regenerate' => false,
            'default_tone' => 'neutral',
            'default_language' => 'id',
            'default_geo' => 'ID',
            'sites' => [],
        ];

        $settings = get_option(self::OPTION_KEY, []);
        $settings = is_array($settings) ? wp_parse_args($settings, $defaults) : $defaults;
        $settings['has_keys'] = $settings['api_mode'] === 'wp' && (bool) get_option(self::API_KEY_OPTION, '');
        return $settings;
    }

    private function resolve_provider_key(): string
    {
        $settings = $this->get_settings();
        if ($settings['api_mode'] !== 'wp') {
            return '';
        }
        $encrypted = get_option(self::API_KEY_OPTION, '');
        if (! $encrypted) {
            return '';
        }
        $decoded = json_decode($this->decrypt($encrypted), true);
        if (! is_array($decoded)) {
            return '';
        }
        $primary = $settings['fallback_order'][0] ?? 'openai';
        return sanitize_text_field($decoded[$primary] ?? '');
    }

    private function encrypt(string $value): string
    {
        $key = $this->encryption_key();
        $iv = random_bytes(16);
        $cipher = openssl_encrypt($value, 'aes-256-cbc', $key, OPENSSL_RAW_DATA, $iv);
        return base64_encode($iv . $cipher);
    }

    private function decrypt(string $payload): string
    {
        $key = $this->encryption_key();
        $raw = base64_decode($payload, true);
        if (! $raw || strlen($raw) <= 16) {
            return '';
        }
        $iv = substr($raw, 0, 16);
        $cipher = substr($raw, 16);
        $plain = openssl_decrypt($cipher, 'aes-256-cbc', $key, OPENSSL_RAW_DATA, $iv);
        return $plain ?: '';
    }

    private function encryption_key(): string
    {
        $seed = wp_salt('auth');
        return substr(hash('sha256', $seed, true), 0, 32);
    }
}

AIO_Content_Suite::bootstrap();
register_activation_hook(__FILE__, [AIO_Content_Suite::class, 'activate']);
