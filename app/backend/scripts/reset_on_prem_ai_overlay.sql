UPDATE ai_runtime_settings
SET payload = payload || '{"deployment_mode":"on_prem","llm_provider":"lm_studio","embedding_provider":"local","local_embedding_server":"lm_studio","mcp_rag_enabled":false}'::jsonb,
    updated_at = NOW()
WHERE id = 1;
SELECT payload->>'llm_provider' AS llm, payload->>'deployment_mode' AS mode
FROM ai_runtime_settings
WHERE id = 1;
