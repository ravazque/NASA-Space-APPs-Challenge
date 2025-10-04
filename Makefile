# ─────────────────────────────────────────────────────────────────────────────
#  EcoStation CGR — Makefile
# ─────────────────────────────────────────────────────────────────────────────

CC       := gcc
CFLAGS   := -O2 -Wall -Wextra -Wshadow -std=c17
DFLAGS   := -O0 -g3 -fsanitize=address,undefined -fno-omit-frame-pointer
INCLUDE  := -Iinclude

SRC_DIR  := src
OBJ_DIR  := objetsLeo

# Núcleo común (sin mains)
CORE_SRCS := cgr.c csv.c heap.c leo_metrics.c nasa_api.c
CORE_OBJS := $(patsubst %.c,$(OBJ_DIR)/%.o,$(CORE_SRCS))

# mains
MAIN_CLI  := $(OBJ_DIR)/main.o        # src/main.c para binario "cgr"
BIN_CLI   := cgr

BIN_LIVE  := cgr_live                 # src/cgr_live.c compila directo
LIVE_SRC  := src/cgr_live.c

# Enlace con libm (fmod) y libcurl (API SODA)
LDLIBS := -lm -lcurl

# time portátil para bench
TIME := $(shell if command -v /usr/bin/time >/dev/null 2>&1; then echo "/usr/bin/time -f 'real %E mem %M KB'"; \
                elif command -v gtime >/dev/null 2>&1; then echo "gtime -f 'real %E mem %M KB'"; \
                else echo "time"; fi)

GREEN  := \033[32m
YELLOW := \033[33m
BLUE   := \033[34m
RED    := \033[31m
RESET  := \033[0m

.PHONY: all clean fclean re run debug help test test-all test_all fuzz bench live

all: $(BIN_CLI) $(BIN_LIVE)
	@echo -e "$(GREEN)✓ Build completo:$(RESET) ./$(BIN_CLI) y ./$(BIN_LIVE)"

# ---------- objetos ----------
$(OBJ_DIR):
	@echo -e "$(YELLOW)→ Creando directorio$(RESET) $(OBJ_DIR)/"
	@mkdir -p $(OBJ_DIR)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	@echo -e "$(BLUE)→ Compilando$(RESET) $< → $@"
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@

# ---------- binarios ----------
$(BIN_CLI): $(CORE_OBJS) $(MAIN_CLI)
	@echo -e "$(BLUE)→ Linkeando$(RESET) $@"
	$(CC) $(CFLAGS) $(CORE_OBJS) $(MAIN_CLI) -o $@ $(LDLIBS)

$(BIN_LIVE): $(CORE_OBJS) $(LIVE_SRC)
	@echo -e "$(BLUE)→ Compilando CGR Live$(RESET)"
	$(CC) $(CFLAGS) $(INCLUDE) $(LIVE_SRC) $(CORE_OBJS) -o $@ $(LDLIBS)

# ---------- atajos ----------
run: $(BIN_CLI)
	@echo -e "$(YELLOW)Demo (k=3, consumo)$(RESET)"
	./$(BIN_CLI) --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k 3 --format text

live: $(BIN_LIVE)
	@echo "Iniciando simulación en tiempo real..."
	./$(BIN_LIVE)

debug: CFLAGS := $(DFLAGS)
debug: fclean all
	@echo -e "$(GREEN)✓ Build debug listo$(RESET)"

clean:
	@echo -e "$(RED)→ Limpiando objetos$(RESET)"
	@rm -rf $(OBJ_DIR)

fclean: clean
	@echo -e "$(RED)→ Limpiando ejecutables$(RESET)"
	@rm -f $(BIN_CLI) $(BIN_LIVE)

re: fclean all

help:
	@echo "Targets: make | run | live | debug | test | fuzz | bench | clean | fclean | re"

# ---------- testing & bench ----------
test: $(BIN_CLI)
	@bash test/run_all.sh

test-all: test
test_all: test

fuzz: $(BIN_CLI)
	@python3 test/gen_cases.py --out test/cases --random 100 --medium --large >/dev/null
	@bash test/run_all.sh

bench: $(BIN_CLI)
	@$(TIME) ./$(BIN_CLI) --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k-yen 10 >/dev/null
