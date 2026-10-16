# jiraview — Canon do Projeto

> **Natureza:** documento **vivo**. Duas zonas:
> - **Determinística (gerada):** entre os marcadores `BEGIN:GENERATED` e `END:GENERATED`.
>   Regenerada de forma **idempotente** por `python3 scripts/harness-setup canon docs/JIRAVIEW_CANONICO.md`.
>   **Nunca editar à mão.**
> - **Semântica (curada):** todo o resto. Curadoria humana; mudanças semânticas só via
>   **proposta** (nunca aplicadas sozinhas). Autonomia com transparência.
>
> Mantido pelo agente de projeto (`jiraview-agent`), que conduz a entrevista de onboarding
> e mantém o backlog em `docs/JIRAVIEW_BACKLOG.md`.

---

## 0. Painel verificado (zona determinística — gerada)

> Como funciona (E2): regenerado por `python3 scripts/harness-setup canon`; idempotente;
> auditoria de drift sem escrever via `--check-only`. O restante deste documento é curadoria
> semântica e **nunca** é sobrescrito por esse comando.

<!-- BEGIN:GENERATED -->
<!-- (bloco gerado — rode `python3 scripts/harness-setup canon` para preencher) -->
<!-- END:GENERATED -->

---

## 1. Finalidade e Núcleo

<!-- Preencher a partir da ENTREVISTA.md — por que o projeto existe, para quem, o que quebra se sumir. -->

## 2. Arquitetura: SSOT canônico + adaptadores finos

<!-- Stack, topologia, onde roda, como reproduzir local; comandos build/test/lint/gate/deploy. -->

## 3. Decisões canônicas

<!-- Decisões com data e motivo (o "porquê"). -->

## 4. Restrições e regras

<!-- Ambiente, compliance, sanitização, dados sensíveis que nunca vazam. -->

## 5. Riscos e dívidas conhecidas

<!-- Fragilidades, acoplamentos, ausências de teste, credenciais frágeis. -->

## 6. Critério de "pronto" (DoD) e checkpoints humanos

<!-- Verificador objetivo; o que exige aprovação humana. -->

## 7. Estado real verificado

<!-- O que foi comprovado (com evidência), não o que se supõe. -->

## 8. Backlog aberto

<!-- Aponta para docs/JIRAVIEW_BACKLOG.md; itens com valor/esforço/risco/aceite. -->

## 9. Perguntas abertas e pontos de debate

<!-- Lacunas registradas pela entrevista; aguardam decisão humana. -->
