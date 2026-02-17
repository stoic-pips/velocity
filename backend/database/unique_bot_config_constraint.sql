-- Enforce one config per user at the database level
ALTER TABLE bot_configs
  ADD CONSTRAINT bot_configs_user_id_unique UNIQUE (user_id);
