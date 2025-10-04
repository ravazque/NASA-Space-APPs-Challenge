
SHELL = /bin/bash
MAKEFLAGS += --no-print-directory

NAME        = leo.a

SRC_DIR     = src
INC_DIR     = include

OBJ_DIR     = leoObjects

CC       = cc
CFLAGS   = -Wall -Wextra -Werror -I$(INC_DIR)
LDFLAGS  = -lreadline

SRCS = $(shell find $(SRC_DIR) -type f -name '*.c')
OBJS = $(SRCS:$(SRC_DIR)/%.c=$(OBJ_DIR)/%.o)

RESET           = \033[0m
TURQUOISE       = \033[0;36m
LIGHT_TURQUOISE = \033[1;36m
LIGHT_GREEN     = \033[1;32m
LIGHT_RED       = \033[1;91m

TOTAL_STEPS = $(words $(SRCS))

define show_progress
	@total=$(TOTAL_STEPS); \
	[ "$$total" -gt 0 ] || total=1; \
	curr=$$(find "$(OBJ_DIR)" -type f -name "*.o" 2>/dev/null | wc -l); \
	width=60; \
	hashes=$$(( curr * width / total )); \
	[ "$$hashes" -ge 0 ] || hashes=0; \
	dots=$$(( width - hashes )); \
	[ "$$dots" -ge 0 ] || dots=0; \
	green=$$(printf "\033[1;32m"); \
	reset=$$(printf "\033[0m"); \
	printf "\rCompiling: ["; \
	bar=$$(printf "%*s" "$$hashes" ""); bar=$${bar// /#}; \
	printf "%s" "$$green$$bar$$reset"; \
	dot=$$(printf "%*s" "$$dots" ""); dot=$${dot// /.}; \
	printf "%s" "$$dot"; \
	printf "] %d/%d" "$$curr" "$$total"; \
	if [ "$$curr" -ge "$$total" ]; then printf " ✓\n"; fi;
endef

all: $(NAME)

$(NAME): $(OBJS)
	@$(CC) $(CFLAGS) $(OBJS) $(LDFLAGS) -o $@
	@echo -e "$(LIGHT_TURQUOISE)Leo ready!$(RESET)"

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	@mkdir -p $(dir $@)
	@$(CC) $(CFLAGS) -c $< -o $@
	$(call show_progress)

$(OBJ_DIR):
	@mkdir -p $@

clean:
	@echo -e "$(LIGHT_RED)Running object cleanup...$(RESET)"
	@rm -rf "$(OBJ_DIR)"
	@echo -e "$(TURQUOISE)Cleaning of objects completed!$(RESET)"

fclean:
	@echo -e "$(LIGHT_RED)Running a full cleanup...$(RESET)"
	@rm -rf "$(OBJ_DIR)"
	@rm -f "$(NAME)"
	@echo -e "$(TURQUOISE)Full cleaning finished!$(RESET)"

re:
	@$(MAKE) fclean
	@$(MAKE) -s all

.PHONY: all clean fclean re
