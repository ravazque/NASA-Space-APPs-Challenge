# ─────────────────────────────────────────────────────────────────────────────
#  EcoStation CGR — Makefile narrado
# ─────────────────────────────────────────────────────────────────────────────
# … (comentarios explicativos iguales a los tuyos) …
# ─────────────────────────────────────────────────────────────────────────────

# ─── Compilador y flags ───────────────────────────────────────────────────────
CC       := gcc
CFLAGS   := -O2 -Wall -Wextra -Wshadow -std=c17
DFLAGS   := -O0 -g3 -fsanitize=address,undefined -fno-omit-frame-pointer
INCLUDE  := -Iinclude

# ─── Directorios ──────────────────────────────────────────────────────────────
SRC_DIR  := src
OBJ_DIR  := objetsLeo

# ─── Detección automática de archivos fuente ─────────────────────────────────
SRC      := $(wildcard $(SRC_DIR)/*.c)
OBJ      := $(patsubst $(SRC_DIR)/%.c,$(OBJ_DIR)/%.o,$(SRC))
BIN      := cgr

# ─── time portátil para bench ────────────────────────────────────────────────
TIME := $(shell if command -v /usr/bin/time >/dev/null 2>&1; then echo "/usr/bin/time -f 'real %E mem %M KB'"; \
                elif command -v gtime >/dev/null 2>&1; then echo "gtime -f 'real %E mem %M KB'"; \
                else echo "time"; fi)

# ─── Colores ANSI ─────────────────────────────────────────────────────────────
GREEN    := \033[32m
YELLOW   := \033[33m
BLUE     := \033[34m
RED      := \033[31m
RESET    := \033[0m

.PHONY: all clean fclean re run debug help test fuzz bench

# ─────────────────────────────────────────────────────────────────────────────
# Build principal
# ─────────────────────────────────────────────────────────────────────────────

all: $(BIN)
	@echo -e "$(GREEN)✓ Build completo:$(RESET) ./$(BIN)"

$(BIN): $(OBJ)
	@echo -e "$(BLUE)→ Linkeando$(RESET) $@"
	$(CC) $(CFLAGS) $(OBJ) -o $@

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	@echo -e "$(BLUE)→ Compilando$(RESET) $< → $@"
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@

$(OBJ_DIR):
	@echo -e "$(YELLOW)→ Creando directorio$(RESET) $(OBJ_DIR)/"
	@mkdir -p $(OBJ_DIR)

# ─────────────────────────────────────────────────────────────────────────────
# Ejecución y debug
# ─────────────────────────────────────────────────────────────────────────────

run: all
	@echo -e "$(YELLOW)Ejecutando demo (k=3, consumo) sobre data/contacts.csv$(RESET)"
	./$(BIN) --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k 3 --format text

debug: CFLAGS := $(DFLAGS)
debug: fclean $(BIN)
	@echo -e "$(GREEN)✓ Build debug listo$(RESET)"
	@echo -e "$(YELLOW)Sugerencia: ejecuta con ASan/UBSan en tu entorno$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# Limpieza
# ─────────────────────────────────────────────────────────────────────────────

clean:
	@echo -e "$(RED)→ Limpiando objetos$(RESET)"
	@rm -rf $(OBJ_DIR)
	@rm -rf test/out
	@rm -rf test/cases

fclean: clean
	@echo -e "$(RED)→ Limpiando ejecutable$(RESET)"
	@rm -f $(BIN)

re: fclean all

# ─────────────────────────────────────────────────────────────────────────────
# Testing & Benchmarking
# ─────────────────────────────────────────────────────────────────────────────

test: $(BIN)
	@echo -e "$(BLUE)→ [TEST] smoke + scenarios$(RESET)"
	@bash test/run_all.sh

fuzz: $(BIN)
	@echo -e "$(BLUE)→ [FUZZ] aleatorios medianos/grandes$(RESET)"
	@python3 test/gen_cases.py --out test/cases --random 100 --medium --large >/dev/null
	@bash test/run_all.sh

bench: $(BIN)
	@echo -e "$(BLUE)→ [BENCH] escalado simple$(RESET)"
	@$(TIME) ./$(BIN) --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k-yen 10 >/dev/null

# ─────────────────────────────────────────────────────────────────────────────
# Testing avanzado
# ─────────────────────────────────────────────────────────────────────────────

test-all: $(BIN)
	@echo -e "$(BLUE)→ [TEST-ALL] Suite completa$(RESET)"
	@bash test/test_all.sh

visualize: $(BIN)
	@echo -e "$(BLUE)→ [VIS] Visualizando ruta$(RESET)"
	@./$(BIN) --contacts data/contacts_realistic.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k-yen 3 > /tmp/cgr_out.json
	@python3 test/visualize_route.py --contacts data/contacts_realistic.csv --json /tmp/cgr_out.json

analyze: $(BIN)
	@echo -e "$(BLUE)→ [ANALYZE] Análisis de diversidad$(RESET)"
	@./$(BIN) --contacts data/contacts_realistic.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k-yen 10 --format text | tee test/out/analysis.txt
	@echo ""
	@echo -e "$(GREEN)Análisis guardado en test/out/analysis.txt$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# CGR Live - Simulación continua
# ─────────────────────────────────────────────────────────────────────────────

cgr_live: $(OBJ_DIR)/cgr.o $(OBJ_DIR)/csv.o $(OBJ_DIR)/heap.o $(OBJ_DIR)/leo_metrics.o $(OBJ_DIR)/nasa_api.o src/cgr_live.c | $(OBJ_DIR)
	@echo -e "$(BLUE)→ Compilando CGR Live$(RESET)"
	$(CC) $(CFLAGS) $(INCLUDE) src/cgr_live.c $(OBJ_DIR)/*.o -o cgr_live

$(OBJ_DIR)/nasa_api.o: src/nasa_api.c | $(OBJ_DIR)
	@echo -e "$(BLUE)→ Compilando NASA API module$(RESET)"
	$(CC) $(CFLAGS) $(INCLUDE) -c src/nasa_api.c -o $(OBJ_DIR)/nasa_api.o

live: cgr_live
	@echo -e "$(YELLOW)Iniciando simulación en tiempo real...$(RESET)"
	./cgr_live

.PHONY: live cgr_live test-all visualize analyze

# ─────────────────────────────────────────────────────────────────────────────
# Ayuda
# ─────────────────────────────────────────────────────────────────────────────

help:
	@echo -e "$(BLUE)═══════════════════════════════════════════════════════════════$(RESET)"
	@echo -e "$(BLUE)  EcoStation CGR - Targets disponibles$(RESET)"
	@echo -e "$(BLUE)═══════════════════════════════════════════════════════════════$(RESET)"
	@echo -e ""
	@echo -e "  $(GREEN)make$(RESET)        → Compila el proyecto"
	@echo -e "  $(GREEN)make run$(RESET)    → Ejecuta demo (k=3, consumo)"
	@echo -e "  $(GREEN)make debug$(RESET)  → Compila con sanitizers (ASan/UBSan)"
	@echo -e "  $(GREEN)make test$(RESET)   → Ejecuta suite de tests"
	@echo -e "  $(GREEN)make fuzz$(RESET)   → Genera casos aleatorios y testea"
	@echo -e "  $(GREEN)make bench$(RESET)  → Ejecuta micro-benchmark"
	@echo -e "  $(GREEN)make clean$(RESET)  → Elimina objetos ($(OBJ_DIR)/)"
	@echo -e "  $(GREEN)make fclean$(RESET) → Elimina objetos + ejecutable"
	@echo -e "  $(GREEN)make re$(RESET)     → Recompila desde cero (fclean + all)"
	@echo -e "  $(GREEN)make help$(RESET)   → Muestra esta ayuda"
	@echo -e ""
	@echo -e "$(BLUE)═══════════════════════════════════════════════════════════════$(RESET)"


