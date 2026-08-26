-- ObservAR: índices para consultas paginadas/ordenadas.
-- Execute SHOW INDEX FROM <tabela> antes de aplicar em um banco já existente.
-- Os nomes abaixo não existem nos modelos atuais do projeto.
-- Faça backup antes de mudanças em produção.

CREATE INDEX ix_medicao_data_hora_id
    ON medicao_qualidade_ar (data_hora DESC, id DESC);

CREATE INDEX ix_estacao_nome_id
    ON estacao_monitoramento (nome, id);

CREATE INDEX ix_log_autenticacao_criado_id
    ON log_autenticacao (criado_em DESC, id DESC);

CREATE INDEX ix_log_acesso_criado_id
    ON log_acesso (criado_em DESC, id DESC);

CREATE INDEX ix_analise_criada_id
    ON analise_interna (criada_em DESC, id DESC);

CREATE INDEX ix_usuario_nome_id
    ON usuario (nome, id);

-- Para filtro por estação + ordenação temporal:
CREATE INDEX ix_medicao_estacao_data_id
    ON medicao_qualidade_ar (estacao_id, data_hora DESC, id DESC);
