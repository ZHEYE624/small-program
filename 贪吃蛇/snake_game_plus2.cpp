/*
 * Snake Game - Complete Implementation (Fixed Map Connectivity)
 * Features: Multiple maps, Endless Mode with 3 speed tiers,
 *           Score-based speed scaling, uniform visual speed, no flicker
 *
 * Fixed: Map2 (Cross Maze) and Map3 (Spiral Dungeon) now have open layouts,
 *        snake starts at (3,3) for all normal maps, speed tuned down.
 */

#include <stdio.h>
#include <stdlib.h>
#include <conio.h>
#include <windows.h>
#include <time.h>

/* ==================== CONSTANTS ==================== */
#define MAX_WIDTH 60
#define MAX_HEIGHT 30
#define MAX_SNAKE_LENGTH 1500
#define MAX_FOOD_COUNT 10
#define MAX_MAPS 4

/* Endless mode speed tiers */
#define ENDLESS_TIER_SLOW 0
#define ENDLESS_TIER_NORMAL 1
#define ENDLESS_TIER_FAST 2

/* Speed parameters for endless mode tiers */
/* Format: {horizontal base delay, vertical multiplier} */
#define ENDLESS_SLOW_H 120
#define ENDLESS_NORMAL_H 85
#define ENDLESS_FAST_H 55

/* Speed scaling: every N points, reduce delay by SCALE_STEP ms */
#define SPEED_SCALE_INTERVAL 50
#define SPEED_SCALE_STEP 5
#define SPEED_MIN_DELAY_H 35
#define SPEED_MIN_DELAY_V 70

/* Console character aspect ratio: height ~ 2x width */
#define VERTICAL_MULTIPLIER 2.0

/* Console colors */
#define COLOR_DEFAULT 7
#define COLOR_WALL 12
#define COLOR_SNAKE_HEAD 10
#define COLOR_SNAKE_BODY 2
#define COLOR_FOOD 14
#define COLOR_EMPTY 0
#define COLOR_TEXT 15
#define COLOR_GOLD 6
#define COLOR_CYAN 11

/* Map symbols */
#define SYMBOL_WALL '#'
#define SYMBOL_EMPTY ' '
#define SYMBOL_SNAKE_HEAD 'O'
#define SYMBOL_SNAKE_BODY 'o'
#define SYMBOL_FOOD '*'

/* Game modes */
#define MODE_NORMAL 0
#define MODE_ENDLESS 1

/* ==================== DATA STRUCTURES ==================== */
typedef struct {
    int x;
    int y;
} Position;

typedef struct {
    Position body[MAX_SNAKE_LENGTH];
    int length;
    int direction; /* 0=Up, 1=Right, 2=Down, 3=Left */
    int nextDirection;
} Snake;

typedef struct {
    Position pos;
    int active;
    int value;
} Food;

typedef struct {
    char name[50];
    int width;
    int height;
    char grid[MAX_HEIGHT][MAX_WIDTH];
    int foodCount;
    int baseSpeedH;  /* Horizontal base speed for normal mode */
    char description[200];
    int mode;
    /* Endless mode specific */
    int endlessTier;     /* 0=Slow, 1=Normal, 2=Fast */
    int endlessBaseH;    /* Starting horizontal delay for endless */
} Map;

/* ==================== GLOBAL VARIABLES ==================== */
Map maps[MAX_MAPS];
int currentMap = 0;
Snake snake;
Food foods[MAX_FOOD_COUNT];
int score = 0;
int steps = 0;
int gameRunning = 0;
int gamePaused = 0;
int totalFoodEaten = 0;
int totalFoodOnMap = 0;
int highScore = 0;

/* Screen buffer for double buffering */
char screenBuffer[MAX_HEIGHT][MAX_WIDTH];
int bufferColor[MAX_HEIGHT][MAX_WIDTH];
Position prevTail;
int currentMoveDelay = 0;

/* ==================== CONSOLE FUNCTIONS ==================== */
void setCursorPosition(int x, int y) {
    COORD coord;
    coord.X = x;
    coord.Y = y;
    SetConsoleCursorPosition(GetStdHandle(STD_OUTPUT_HANDLE), coord);
}

void setConsoleColor(int color) {
    SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE), color);
}

void hideCursor() {
    CONSOLE_CURSOR_INFO cursorInfo;
    cursorInfo.bVisible = FALSE;
    cursorInfo.dwSize = 1;
    SetConsoleCursorInfo(GetStdHandle(STD_OUTPUT_HANDLE), &cursorInfo);
}

void clearScreen() {
    system("cls");
}

/* ==================== DOUBLE BUFFER SYSTEM ==================== */
void initBuffer() {
    int i, j;
    for (i = 0; i < MAX_HEIGHT; i++) {
        for (j = 0; j < MAX_WIDTH; j++) {
            screenBuffer[i][j] = ' ';
            bufferColor[i][j] = COLOR_EMPTY;
        }
    }
}

void drawChar(int x, int y, char ch, int color) {
    if (screenBuffer[y][x] != ch || bufferColor[y][x] != color) {
        setCursorPosition(x + 2, y + 3);
        setConsoleColor(color);
        printf("%c", ch);
        screenBuffer[y][x] = ch;
        bufferColor[y][x] = color;
    }
}

void eraseChar(int x, int y) {
    Map *m = &maps[currentMap];
    if (x >= 0 && x < m->width && y >= 0 && y < m->height) {
        if (m->grid[y][x] == SYMBOL_WALL) {
            drawChar(x, y, SYMBOL_WALL, COLOR_WALL);
        } else {
            drawChar(x, y, ' ', COLOR_EMPTY);
        }
    }
}

/* ==================== DYNAMIC SPEED SYSTEM ==================== */
int getCurrentBaseDelayH() {
    Map *m = &maps[currentMap];
    int base = m->endlessBaseH;
    int reduction;

    if (m->mode != MODE_ENDLESS) {
        return m->baseSpeedH;
    }

    reduction = (score / SPEED_SCALE_INTERVAL) * SPEED_SCALE_STEP;
    if (base - reduction < SPEED_MIN_DELAY_H) {
        return SPEED_MIN_DELAY_H;
    }
    return base - reduction;
}

int getMoveDelay(int direction) {
    int baseH = getCurrentBaseDelayH();
    if (direction == 0 || direction == 2) {
        int delayV = (int)(baseH * VERTICAL_MULTIPLIER);
        if (delayV < SPEED_MIN_DELAY_V) {
            delayV = SPEED_MIN_DELAY_V;
        }
        return delayV;
    }
    return baseH;
}

/* ==================== MAP DEFINITIONS (FIXED) ==================== */
void initializeMaps() {
    int i, j;

    /* ---------- Map 1: Classic Box (Easy) ---------- */
    strcpy(maps[0].name, "Classic Box");
    strcpy(maps[0].description, "Standard rectangular arena. Perfect for beginners.");
    maps[0].width = 20;
    maps[0].height = 15;
    maps[0].foodCount = 5;
    maps[0].baseSpeedH = 140;          /* Slowed down */
    maps[0].mode = MODE_NORMAL;
    maps[0].endlessTier = -1;
    maps[0].endlessBaseH = 0;

    for (i = 0; i < maps[0].height; i++) {
        for (j = 0; j < maps[0].width; j++) {
            if (i == 0 || i == maps[0].height - 1 || j == 0 || j == maps[0].width - 1)
                maps[0].grid[i][j] = SYMBOL_WALL;
            else
                maps[0].grid[i][j] = SYMBOL_EMPTY;
        }
    }

    /* ---------- Map 2: Cross Maze (Medium) - Fixed: no closed loop ---------- */
    strcpy(maps[1].name, "Cross Maze");
    strcpy(maps[1].description, "A cross-shaped obstacle that does not trap you.");
    maps[1].width = 30;
    maps[1].height = 20;
    maps[1].foodCount = 7;
    maps[1].baseSpeedH = 100;          /* Slowed down */
    maps[1].mode = MODE_NORMAL;
    maps[1].endlessTier = -1;
    maps[1].endlessBaseH = 0;

    // First, draw outer walls, then inner cross
    for (i = 0; i < maps[1].height; i++) {
        for (j = 0; j < maps[1].width; j++) {
            if (i == 0 || i == maps[1].height - 1 || j == 0 || j == maps[1].width - 1)
                maps[1].grid[i][j] = SYMBOL_WALL;
            else
                maps[1].grid[i][j] = SYMBOL_EMPTY;
        }
    }
    // Vertical bar: x = 15, y from 6 to 14 (inclusive)
    for (i = 6; i <= 14; i++) {
        maps[1].grid[i][15] = SYMBOL_WALL;
    }
    // Horizontal bar: y = 10, x from 10 to 20 (inclusive)
    for (j = 10; j <= 20; j++) {
        maps[1].grid[10][j] = SYMBOL_WALL;
    }
    // The cross does not connect to the outer walls, so all four quadrants are accessible.

    /* ---------- Map 3: Obstacle Field (Hard) - Fixed: isolated walls, no loops ---------- */
    strcpy(maps[2].name, "Obstacle Field");
    strcpy(maps[2].description, "Several isolated walls - challenging but fair.");
    maps[2].width = 35;
    maps[2].height = 22;
    maps[2].foodCount = 10;
    maps[2].baseSpeedH = 80;           /* Slowed down */
    maps[2].mode = MODE_NORMAL;
    maps[2].endlessTier = -1;
    maps[2].endlessBaseH = 0;

    // Draw outer walls
    for (i = 0; i < maps[2].height; i++) {
        for (j = 0; j < maps[2].width; j++) {
            if (i == 0 || i == maps[2].height - 1 || j == 0 || j == maps[2].width - 1)
                maps[2].grid[i][j] = SYMBOL_WALL;
            else
                maps[2].grid[i][j] = SYMBOL_EMPTY;
        }
    }

    // Add several short, isolated wall segments (none touch each other or the border)
    // Vertical segment 1: x=8, y=4..8
    for (i = 4; i <= 8; i++) maps[2].grid[i][8] = SYMBOL_WALL;
    // Vertical segment 2: x=26, y=13..17
    for (i = 13; i <= 17; i++) maps[2].grid[i][26] = SYMBOL_WALL;
    // Horizontal segment 1: y=6, x=12..18
    for (j = 12; j <= 18; j++) maps[2].grid[6][j] = SYMBOL_WALL;
    // Horizontal segment 2: y=15, x=5..10
    for (j = 5; j <= 10; j++) maps[2].grid[15][j] = SYMBOL_WALL;
    // A few single-cell walls for variety
    maps[2].grid[18][20] = SYMBOL_WALL;
    maps[2].grid[12][30] = SYMBOL_WALL;
    maps[2].grid[5][25] = SYMBOL_WALL;

    /* ---------- Map 4: Endless Arena (unchanged) ---------- */
    strcpy(maps[3].name, "Endless Arena");
    strcpy(maps[3].description, "Large open space. Speed increases with score!");
    maps[3].width = 50;
    maps[3].height = 26;
    maps[3].foodCount = 1;
    maps[3].baseSpeedH = 0;
    maps[3].mode = MODE_ENDLESS;
    maps[3].endlessTier = ENDLESS_TIER_NORMAL;
    maps[3].endlessBaseH = ENDLESS_NORMAL_H;

    // Fill with empty (outer walls will be drawn in drawStaticMap from grid, but we need to set grid)
    for (i = 0; i < maps[3].height; i++) {
        for (j = 0; j < maps[3].width; j++) {
            if (i == 0 || i == maps[3].height - 1 || j == 0 || j == maps[3].width - 1)
                maps[3].grid[i][j] = SYMBOL_WALL;
            else
                maps[3].grid[i][j] = SYMBOL_EMPTY;
        }
    }
}

/* ==================== DRAWING FUNCTIONS ==================== */
void drawStaticMap() {
    int i, j;
    Map *m = &maps[currentMap];

    for (i = 0; i < m->height; i++) {
        for (j = 0; j < m->width; j++) {
            if (m->grid[i][j] == SYMBOL_WALL) {
                drawChar(j, i, SYMBOL_WALL, COLOR_WALL);
            } else {
                drawChar(j, i, ' ', COLOR_EMPTY);
            }
        }
    }
}

void drawSnakeHead() {
    drawChar(snake.body[0].x, snake.body[0].y, SYMBOL_SNAKE_HEAD, COLOR_SNAKE_HEAD);
}

void drawSnakeBody() {
    int i;
    for (i = 1; i < snake.length; i++) {
        drawChar(snake.body[i].x, snake.body[i].y, SYMBOL_SNAKE_BODY, COLOR_SNAKE_BODY);
    }
}

void eraseTail() {
    eraseChar(prevTail.x, prevTail.y);
}

void drawFood() {
    int i;
    for (i = 0; i < MAX_FOOD_COUNT; i++) {
        if (foods[i].active) {
            if (maps[currentMap].mode == MODE_ENDLESS) {
                drawChar(foods[i].pos.x, foods[i].pos.y, SYMBOL_FOOD, COLOR_GOLD);
            } else {
                drawChar(foods[i].pos.x, foods[i].pos.y, SYMBOL_FOOD, COLOR_FOOD);
            }
        }
    }
}

/* ==================== INFO PANEL ==================== */
int lastScore = -1;
int lastSteps = -1;
int lastHighScore = -1;
int lastLength = -1;
int lastFoodEaten = -1;
int lastTotalFood = -1;
int lastSpeedInfo = -1;

void resetInfoCache() {
    lastScore = -1;
    lastSteps = -1;
    lastHighScore = -1;
    lastLength = -1;
    lastFoodEaten = -1;
    lastTotalFood = -1;
    lastSpeedInfo = -1;
}

void drawInfoPanel() {
    int infoX = 60;
    Map *m = &maps[currentMap];
    int currentDelayH = getCurrentBaseDelayH();

    if (m->mode == MODE_ENDLESS) {
        infoX = 56;
    }

    setCursorPosition(infoX, 3);
    setConsoleColor(COLOR_TEXT);
    printf("=== GAME INFO ===");

    setCursorPosition(infoX, 5);
    printf("Map: %s", m->name);

    setCursorPosition(infoX, 6);
    if (m->mode == MODE_ENDLESS) {
        setConsoleColor(14);
        printf("MODE: ENDLESS");
        setConsoleColor(COLOR_TEXT);
    } else {
        printf("Difficulty: %s", currentMap == 0 ? "Easy" : (currentMap == 1 ? "Medium" : "Hard"));
    }

    if (score != lastScore) {
        setCursorPosition(infoX, 8);
        setConsoleColor(14);
        printf("Score: %-10d", score);
        lastScore = score;
    }

    if (steps != lastSteps) {
        setCursorPosition(infoX, 9);
        setConsoleColor(14);
        printf("Steps: %-10d", steps);
        lastSteps = steps;
    }

    if (m->mode == MODE_ENDLESS) {
        setCursorPosition(infoX, 10);
        setConsoleColor(COLOR_CYAN);
        if (m->endlessTier == ENDLESS_TIER_SLOW) {
            printf("Tier: SLOW  ");
        } else if (m->endlessTier == ENDLESS_TIER_NORMAL) {
            printf("Tier: NORMAL");
        } else {
            printf("Tier: FAST  ");
        }
        setConsoleColor(COLOR_TEXT);

        if (currentDelayH != lastSpeedInfo) {
            setCursorPosition(infoX, 11);
            setConsoleColor(12);
            printf("Speed: %dms", currentDelayH);
            lastSpeedInfo = currentDelayH;
        }

        if (highScore != lastHighScore) {
            setCursorPosition(infoX, 12);
            setConsoleColor(14);
            printf("High Score: %-10d", highScore);
            lastHighScore = highScore;
        }
        if (snake.length != lastLength) {
            setCursorPosition(infoX, 13);
            setConsoleColor(14);
            printf("Snake Length: %-10d", snake.length);
            lastLength = snake.length;
        }
    } else {
        if (totalFoodEaten != lastFoodEaten || totalFoodOnMap != lastTotalFood) {
            setCursorPosition(infoX, 10);
            setConsoleColor(14);
            printf("Food: %d/%d%-10s", totalFoodEaten, totalFoodOnMap, "");
            lastFoodEaten = totalFoodEaten;
            lastTotalFood = totalFoodOnMap;
        }
    }

    setCursorPosition(infoX, 15);
    setConsoleColor(COLOR_TEXT);
    printf("=== CONTROLS ===");

    setCursorPosition(infoX, 17);
    printf("W / Up    : Move Up");
    setCursorPosition(infoX, 18);
    printf("S / Down  : Move Down");
    setCursorPosition(infoX, 19);
    printf("A / Left  : Move Left");
    setCursorPosition(infoX, 20);
    printf("D / Right : Move Right");

    setCursorPosition(infoX, 22);
    printf("P         : Pause");
    setCursorPosition(infoX, 23);
    printf("Q / ESC   : Quit");

    setCursorPosition(infoX, 25);
    printf("=== LEGEND ===");
    setCursorPosition(infoX, 27);
    setConsoleColor(COLOR_SNAKE_HEAD);
    printf("%c", SYMBOL_SNAKE_HEAD);
    setConsoleColor(COLOR_TEXT);
    printf(" Snake Head");

    setCursorPosition(infoX, 28);
    setConsoleColor(COLOR_SNAKE_BODY);
    printf("%c", SYMBOL_SNAKE_BODY);
    setConsoleColor(COLOR_TEXT);
    printf(" Snake Body");

    setCursorPosition(infoX, 29);
    if (m->mode == MODE_ENDLESS) {
        setConsoleColor(COLOR_GOLD);
    } else {
        setConsoleColor(COLOR_FOOD);
    }
    printf("%c", SYMBOL_FOOD);
    setConsoleColor(COLOR_TEXT);
    printf(" Food");

    setCursorPosition(infoX, 30);
    setConsoleColor(COLOR_WALL);
    printf("%c", SYMBOL_WALL);
    setConsoleColor(COLOR_TEXT);
    printf(" Wall");

    setConsoleColor(COLOR_DEFAULT);
}

/* ==================== GAME LOGIC ==================== */
int isValidPosition(int x, int y) {
    int i;
    Map *m = &maps[currentMap];

    if (x < 0 || x >= m->width || y < 0 || y >= m->height)
        return 0;

    if (m->grid[y][x] == SYMBOL_WALL)
        return 0;

    for (i = 0; i < snake.length; i++) {
        if (snake.body[i].x == x && snake.body[i].y == y)
            return 0;
    }

    return 1;
}

int isFoodPosition(int x, int y) {
    int i;
    for (i = 0; i < MAX_FOOD_COUNT; i++) {
        if (foods[i].active && foods[i].pos.x == x && foods[i].pos.y == y)
            return 1;
    }
    return 0;
}

void spawnFood() {
    int i;
    Map *m = &maps[currentMap];

    for (i = 0; i < MAX_FOOD_COUNT; i++) {
        if (!foods[i].active) {
            int x, y;
            int attempts = 0;
            do {
                x = rand() % (m->width - 2) + 1;
                y = rand() % (m->height - 2) + 1;
                attempts++;
                if (attempts > 1000) {
                    int fx, fy;
                    for (fy = 1; fy < m->height - 1; fy++) {
                        for (fx = 1; fx < m->width - 1; fx++) {
                            if (isValidPosition(fx, fy) && !isFoodPosition(fx, fy)) {
                                x = fx;
                                y = fy;
                                break;
                            }
                        }
                    }
                    break;
                }
            } while (!isValidPosition(x, y) || isFoodPosition(x, y));

            foods[i].pos.x = x;
            foods[i].pos.y = y;
            foods[i].active = 1;
            foods[i].value = 10;
            break;
        }
    }
}

void initializeGame() {
    int i;
    Map *m = &maps[currentMap];

    snake.length = 3;
    // All normal maps start at (3,3) to ensure they are in an open area
    // For endless map, it's also safe because it's open
    snake.body[0].x = 3;
    snake.body[0].y = 3;
    snake.body[1].x = 2;
    snake.body[1].y = 3;
    snake.body[2].x = 1;
    snake.body[2].y = 3;
    snake.direction = 1;
    snake.nextDirection = 1;

    prevTail.x = snake.body[snake.length - 1].x;
    prevTail.y = snake.body[snake.length - 1].y;

    currentMoveDelay = getMoveDelay(snake.direction);

    for (i = 0; i < MAX_FOOD_COUNT; i++) {
        foods[i].active = 0;
    }

    if (m->mode == MODE_ENDLESS) {
        totalFoodOnMap = 999999;
    } else {
        totalFoodOnMap = m->foodCount * 3;
    }
    totalFoodEaten = 0;
    score = 0;
    steps = 0;
    gameRunning = 1;
    gamePaused = 0;

    resetInfoCache();
    initBuffer();

    if (m->mode == MODE_ENDLESS) {
        spawnFood();
    } else {
        for (i = 0; i < m->foodCount; i++) {
            spawnFood();
        }
    }
}

int moveSnake() {
    int i;
    Position newHead;
    int ateFood = -1;

    prevTail.x = snake.body[snake.length - 1].x;
    prevTail.y = snake.body[snake.length - 1].y;

    if (snake.nextDirection != -1) {
        if (!((snake.direction == 0 && snake.nextDirection == 2) ||
              (snake.direction == 2 && snake.nextDirection == 0) ||
              (snake.direction == 1 && snake.nextDirection == 3) ||
              (snake.direction == 3 && snake.nextDirection == 1))) {
            snake.direction = snake.nextDirection;
        }
    }

    currentMoveDelay = getMoveDelay(snake.direction);

    newHead = snake.body[0];
    switch (snake.direction) {
        case 0: newHead.y--; break;
        case 1: newHead.x++; break;
        case 2: newHead.y++; break;
        case 3: newHead.x--; break;
    }

    if (!isValidPosition(newHead.x, newHead.y)) {
        return 0;
    }

    for (i = 0; i < snake.length - 1; i++) {
        if (snake.body[i].x == newHead.x && snake.body[i].y == newHead.y) {
            return 0;
        }
    }

    for (i = 0; i < MAX_FOOD_COUNT; i++) {
        if (foods[i].active && foods[i].pos.x == newHead.x && foods[i].pos.y == newHead.y) {
            ateFood = i;
            break;
        }
    }

    if (ateFood == -1) {
        for (i = snake.length - 1; i > 0; i--) {
            snake.body[i] = snake.body[i - 1];
        }
        snake.body[0] = newHead;
    } else {
        snake.length++;
        for (i = snake.length - 1; i > 0; i--) {
            snake.body[i] = snake.body[i - 1];
        }
        snake.body[0] = newHead;

        foods[ateFood].active = 0;
        score += foods[ateFood].value;
        totalFoodEaten++;

        if (score > highScore) {
            highScore = score;
        }

        spawnFood();
    }

    steps++;
    return 1;
}

/* ==================== OPTIMIZED RENDER ==================== */
void renderFrame() {
    eraseTail();

    if (snake.length > 1) {
        drawChar(snake.body[1].x, snake.body[1].y, SYMBOL_SNAKE_BODY, COLOR_SNAKE_BODY);
    }

    drawSnakeHead();
    drawFood();
    drawInfoPanel();
}

void fullRender() {
    drawStaticMap();
    drawFood();
    drawSnakeHead();
    drawSnakeBody();
    drawInfoPanel();
}

/* ==================== SCREENS ==================== */
void showTitleScreen() {
    clearScreen();
    setConsoleColor(COLOR_TEXT);

    setCursorPosition(20, 5);
    printf("========================================");
    setCursorPosition(20, 6);
    printf("||          S N A K E   G A M E       ||");
    setCursorPosition(20, 7);
    printf("========================================");

    setCursorPosition(20, 10);
    printf("A classic arcade game implemented in C");
    setCursorPosition(20, 11);
    printf("Navigate the snake, eat food, grow long!");
    setCursorPosition(20, 12);
    printf("Avoid walls and your own tail.");

    setCursorPosition(20, 15);
    setConsoleColor(COLOR_FOOD);
    printf("    ****    ");
    setCursorPosition(20, 16);
    printf("   *    *   ");
    setCursorPosition(20, 17);
    printf("   * oo *   ");
    setCursorPosition(20, 18);
    printf("   * oo *   ");
    setCursorPosition(20, 19);
    printf("    ****    ");
    setConsoleColor(COLOR_TEXT);

    setCursorPosition(20, 22);
    printf("Press any key to continue...");
}

void showMapSelection() {
    int i;
    int choice;
    clearScreen();

    setCursorPosition(20, 3);
    printf("========================================");
    setCursorPosition(20, 4);
    printf("||      SELECT MAP / DIFFICULTY       ||");
    setCursorPosition(20, 5);
    printf("========================================");

    for (i = 0; i < MAX_MAPS; i++) {
        setCursorPosition(20, 8 + i * 4);
        if (maps[i].mode == MODE_ENDLESS) {
            setConsoleColor(14);
            printf("[%d] %s [ENDLESS]", i + 1, maps[i].name);
            setConsoleColor(COLOR_TEXT);
        } else {
            printf("[%d] %s", i + 1, maps[i].name);
        }
        setCursorPosition(22, 9 + i * 4);
        printf("Size: %dx%d | Food: %s | Speed: %s",
               maps[i].width, maps[i].height,
               maps[i].mode == MODE_ENDLESS ? "1 (respawn)" : "Multiple",
               i == 0 ? "Slow" : (i == 1 ? "Normal" : (i == 2 ? "Fast" : "Tier-based")));
        setCursorPosition(22, 10 + i * 4);
        printf("%s", maps[i].description);
    }

    setCursorPosition(20, 26);
    printf("Enter your choice (1-%d): ", MAX_MAPS);

    do {
        choice = _getch() - '0';
    } while (choice < 1 || choice > MAX_MAPS);

    currentMap = choice - 1;
}

void showEndlessTierSelection() {
    int choice;
    clearScreen();

    setCursorPosition(20, 3);
    printf("========================================");
    setCursorPosition(20, 4);
    printf("||     ENDLESS MODE: SELECT SPEED     ||");
    setCursorPosition(20, 5);
    printf("========================================");

    setCursorPosition(20, 8);
    printf("Choose your starting speed tier:");
    setCursorPosition(20, 10);

    setConsoleColor(10);
    printf("[1] SLOW");
    setConsoleColor(COLOR_TEXT);
    setCursorPosition(22, 11);
    printf("Starting: %dms | Relaxed pace", ENDLESS_SLOW_H);
    setCursorPosition(22, 12);
    printf("Speed increases every %d points", SPEED_SCALE_INTERVAL);

    setCursorPosition(20, 14);
    setConsoleColor(14);
    printf("[2] NORMAL");
    setConsoleColor(COLOR_TEXT);
    setCursorPosition(22, 15);
    printf("Starting: %dms | Balanced challenge", ENDLESS_NORMAL_H);
    setCursorPosition(22, 16);
    printf("Speed increases every %d points", SPEED_SCALE_INTERVAL);

    setCursorPosition(20, 18);
    setConsoleColor(12);
    printf("[3] FAST");
    setConsoleColor(COLOR_TEXT);
    setCursorPosition(22, 19);
    printf("Starting: %dms | Intense action", ENDLESS_FAST_H);
    setCursorPosition(22, 20);
    printf("Speed increases every %d points", SPEED_SCALE_INTERVAL);

    setCursorPosition(20, 23);
    printf("Speed will increase as your score grows!");
    setCursorPosition(20, 24);
    printf("Max speed cap: %dms (horizontal)", SPEED_MIN_DELAY_H);

    setCursorPosition(20, 26);
    printf("Enter your choice (1-3): ");

    do {
        choice = _getch() - '0';
    } while (choice < 1 || choice > 3);

    maps[3].endlessTier = choice - 1;
    if (choice == 1) {
        maps[3].endlessBaseH = ENDLESS_SLOW_H;
    } else if (choice == 2) {
        maps[3].endlessBaseH = ENDLESS_NORMAL_H;
    } else {
        maps[3].endlessBaseH = ENDLESS_FAST_H;
    }
}

void showGameOverScreen(int won) {
    clearScreen();
    setConsoleColor(COLOR_TEXT);

    setCursorPosition(25, 8);
    if (won) {
        setConsoleColor(10);
        printf("*** CONGRATULATIONS! ***");
    } else {
        setConsoleColor(12);
        printf("*** GAME OVER ***");
    }
    setConsoleColor(COLOR_TEXT);

    setCursorPosition(25, 11);
    printf("Final Score: %d", score);
    setCursorPosition(25, 12);
    printf("Total Steps: %d", steps);
    setCursorPosition(25, 13);
    printf("Snake Length: %d", snake.length);
    setCursorPosition(25, 14);
    printf("Food Eaten: %d", totalFoodEaten);

    if (maps[currentMap].mode == MODE_ENDLESS && score == highScore && score > 0) {
        setCursorPosition(25, 16);
        setConsoleColor(14);
        printf("*** NEW HIGH SCORE! ***");
        setConsoleColor(COLOR_TEXT);
    }

    setCursorPosition(25, 18);
    printf("Press [R] to Restart");
    setCursorPosition(25, 19);
    printf("Press [M] for Main Menu");
    setCursorPosition(25, 20);
    printf("Press [Q] to Quit");
}

void showPauseScreen() {
    setCursorPosition(20, 12);
    setConsoleColor(14);
    printf("*** GAME PAUSED ***");
    setCursorPosition(20, 14);
    printf("Press [P] to Resume");
    setCursorPosition(20, 15);
    printf("Press [Q] to Quit to Menu");
    setConsoleColor(COLOR_DEFAULT);
}

void clearPauseScreen() {
    setCursorPosition(20, 12);
    printf("                   ");
    setCursorPosition(20, 14);
    printf("                       ");
    setCursorPosition(20, 15);
    printf("                         ");
}

/* ==================== MAIN GAME LOOP ==================== */
void gameLoop() {
    int key;
    int running = 1;
    int gameOver = 0;
    int won = 0;

    clearScreen();
    setConsoleColor(COLOR_TEXT);
    setCursorPosition(2, 1);
    if (maps[currentMap].mode == MODE_ENDLESS) {
        printf("SNAKE GAME - %s [ENDLESS MODE]", maps[currentMap].name);
    } else {
        printf("SNAKE GAME - %s", maps[currentMap].name);
    }

    fullRender();

    while (running) {
        if (_kbhit()) {
            key = _getch();

            if (key == 224 || key == 0) {
                key = _getch();
                switch (key) {
                    case 72: snake.nextDirection = 0; break;
                    case 77: snake.nextDirection = 1; break;
                    case 80: snake.nextDirection = 2; break;
                    case 75: snake.nextDirection = 3; break;
                }
            } else {
                switch (key) {
                    case 'w': case 'W': snake.nextDirection = 0; break;
                    case 'd': case 'D': snake.nextDirection = 1; break;
                    case 's': case 'S': snake.nextDirection = 2; break;
                    case 'a': case 'A': snake.nextDirection = 3; break;
                    case 'p': case 'P':
                        gamePaused = !gamePaused;
                        if (gamePaused) {
                            showPauseScreen();
                        } else {
                            clearPauseScreen();
                        }
                        break;
                    case 'q': case 'Q': case 27:
                        running = 0;
                        break;
                }
            }
        }

        if (gamePaused || !gameRunning) {
            Sleep(50);
            continue;
        }

        if (!moveSnake()) {
            gameOver = 1;
            running = 0;
        }

        if (maps[currentMap].mode == MODE_NORMAL && totalFoodEaten >= totalFoodOnMap) {
            won = 1;
            gameOver = 1;
            running = 0;
        }

        if (running) {
            renderFrame();
        }

        Sleep(currentMoveDelay);
    }

    if (gameOver) {
        showGameOverScreen(won);

        while (1) {
            key = _getch();
            if (key == 'r' || key == 'R') {
                initializeGame();
                gameLoop();
                return;
            } else if (key == 'm' || key == 'M') {
                return;
            } else if (key == 'q' || key == 'Q' || key == 27) {
                exit(0);
            }
        }
    }
}

/* ==================== MAIN FUNCTION ==================== */
int main() {
    int running = 1;
    int key;

    srand((unsigned)time(NULL));
    hideCursor();
    initializeMaps();

    while (running) {
        showTitleScreen();
        _getch();

        showMapSelection();

        if (maps[currentMap].mode == MODE_ENDLESS) {
            showEndlessTierSelection();
        }

        initializeGame();
        gameLoop();

        clearScreen();
        setCursorPosition(25, 10);
        printf("Thanks for playing Snake Game!");
        setCursorPosition(25, 12);
        printf("Press [Enter] to return to Main Menu");
        setCursorPosition(25, 13);
        printf("Press [Q] to Exit");

        key = _getch();
        if (key == 'q' || key == 'Q' || key == 27) {
            running = 0;
        }
    }

    clearScreen();
    setCursorPosition(25, 12);
    printf("Goodbye! Thanks for playing!");
    setCursorPosition(0, 25);

    return 0;
}