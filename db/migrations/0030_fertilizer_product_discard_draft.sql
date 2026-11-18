-- 0030: a draft fertilizer_product can be discarded (deleted). Active rows stay frozen: no
-- policy here or in 0027 lets anyone update or delete a row whose status is 'active'.
--
-- Who, same as the draft UPDATE policies in 0027:
--   cp_app    a human superadmin context, through app_ctx_platform_role().
--   cp_admin  the CLI: no context, or a human one. A service context is refused.
--
-- Stops if another table already has a foreign key to the catalog: discarding was approved on
-- the basis that nothing references a product yet. recommendation_line.product_id (0026) has
-- no foreign key and nothing writes it. When product matching adds that key, deleting a
-- referenced draft fails and the app shows a plain refusal.
set local role cp_migrator;

do $$
begin
  if exists (select 1 from pg_catalog.pg_constraint
             where contype = 'f' and confrelid = 'public.fertilizer_product'::regclass) then
    raise exception 'fertilizer_product is referenced by a foreign key: review draft discard';
  end if;
end
$$;

grant delete on fertilizer_product to cp_app;

create policy fertilizer_product_delete on fertilizer_product
  for delete to cp_app
  using (status = 'draft' and (select public.app_ctx_platform_role()) = 'superadmin');

create policy fertilizer_product_admin_delete on fertilizer_product
  for delete to cp_admin
  using (status = 'draft'
         and ((select public.app_ctx_user()) is null or (select public.app_ctx_is_human())));
