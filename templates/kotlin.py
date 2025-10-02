"""
Professional Kotlin Code Templates for Modern Android Development
Comprehensive, production-ready templates following latest Android best practices
"""


    from jinja2 import Template

# ... (rest of the imports)

class KotlinTemplateGenerator:
    """Generates professional, modern Kotlin templates for Android development"""
    
    def __init__(self, config: TemplateConfig):
        self.config = config

    def _render_template(self, template_path: str, context: Dict) -> str:
        """Render a Jinja2 template."""
        with open(template_path, "r") as f:
            template_string = f.read()
        template = Template(template_string)
        return template.render(context)

    # ============================================================================
    # MVVM ARCHITECTURE TEMPLATES
    # ============================================================================
    
    def generate_viewmodel_template(self, entity_name: str) -> str:
        """Generate a comprehensive ViewModel following MVVM best practices"""
        context = {
            "package_name": self.config.package_name,
            "entity_name": entity_name,
        }
        return self._render_template("templates/kotlin/viewmodel.kt.template", context)

    def generate_repository_template(self, entity_name: str) -> str:
        """Generate a comprehensive Repository implementation"""
        context = {
            "package_name": self.config.package_name,
            "entity_name": entity_name,
        }
        return self._render_template("templates/kotlin/repository.kt.template", context)

    def generate_room_dao_template(self, entity_name: str) -> str:
        """Generate a comprehensive Room DAO"""
        return f"""package {self.config.package_name}.data.local.dao

import androidx.room.*
import kotlinx.coroutines.flow.Flow
import {self.config.package_name}.data.local.entity.{entity_name}Entity

/**
 * Data Access Object for {entity_name}Entity
 * 
 * Provides type-safe database operations with:
 * - Reactive queries using Flow
 * - Suspend functions for async operations
 * - Compile-time SQL validation
 * - Automatic type conversion
 * 
 * Best Practices:
 * - Return Flow for observable queries (auto-updates UI)
 * - Use suspend for single-shot operations
 * - Leverage @Transaction for complex operations
 * - Use @Query for custom queries with type-safe parameters
 */
@Dao
interface {entity_name}Dao {{

    /**
     * Get all {entity_name.lower()}s ordered by creation date (newest first)
     * Returns Flow for automatic UI updates when data changes
     */
    @Query("SELECT * FROM {entity_name.lower()}s ORDER BY createdAt DESC")
    fun getAll{entity_name}s(): Flow<List<{entity_name}Entity>>

    /**
     * Get a single {entity_name.lower()} by ID
     * Returns nullable for handling not found cases
     */
    @Query("SELECT * FROM {entity_name.lower()}s WHERE id = :id")
    suspend fun get{entity_name}ById(id: String): {entity_name}Entity?

    /**
     * Search {entity_name.lower()}s by name (case-insensitive)
     * Uses LIKE operator with wildcards for partial matching
     */
    @Query(\"\"\"
        SELECT * FROM {entity_name.lower()}s 
        WHERE name LIKE '%' || :query || '%' 
        OR description LIKE '%' || :query || '%'
        ORDER BY createdAt DESC
    \"\"\")
    fun search{entity_name}s(query: String): Flow<List<{entity_name}Entity>>

    /**
     * Get {entity_name.lower()}s created after a specific date
     * Useful for syncing incremental updates
     */
    @Query("SELECT * FROM {entity_name.lower()}s WHERE createdAt > :timestamp ORDER BY createdAt DESC")
    fun get{entity_name}sAfter(timestamp: Long): Flow<List<{entity_name}Entity>>

    /**
     * Get {entity_name.lower()}s with pending sync (offline changes)
     */
    @Query("SELECT * FROM {entity_name.lower()}s WHERE pendingSync = 1")
    suspend fun getPending{entity_name}s(): List<{entity_name}Entity>

    /**
     * Insert a single {entity_name.lower()}
     * OnConflictStrategy.REPLACE updates existing entry if conflict occurs
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert{entity_name}({entity_name.lower()}: {entity_name}Entity): Long

    /**
     * Insert multiple {entity_name.lower()}s
     * Returns list of row IDs for inserted items
     */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll{entity_name}s({entity_name.lower()}s: List<{entity_name}Entity>): List<Long>

    /**
     * Update an existing {entity_name.lower()}
     * Returns number of rows updated (0 if not found, 1 if updated)
     */
    @Update
    suspend fun update{entity_name}({entity_name.lower()}: {entity_name}Entity): Int

    /**
     * Delete a single {entity_name.lower()}
     */
    @Delete
    suspend fun delete{entity_name}({entity_name.lower()}: {entity_name}Entity): Int

    /**
     * Delete {entity_name.lower()} by ID
     */
    @Query("DELETE FROM {entity_name.lower()}s WHERE id = :id")
    suspend fun delete{entity_name}ById(id: String): Int

    /**
     * Delete all {entity_name.lower()}s
     * Use with caution - typically for cache clearing
     */
    @Query("DELETE FROM {entity_name.lower()}s")
    suspend fun deleteAll{entity_name}s(): Int

    /**
     * Mark {entity_name.lower()} for deletion (soft delete for offline support)
     */
    @Query("UPDATE {entity_name.lower()}s SET markedForDeletion = 1, pendingSync = 1 WHERE id = :id")
    suspend fun mark{entity_name}ForDeletion(id: String): Int

    /**
     * Get count of all {entity_name.lower()}s
     */
    @Query("SELECT COUNT(*) FROM {entity_name.lower()}s")
    suspend fun get{entity_name}Count(): Int

    /**
     * Check if {entity_name.lower()} exists by ID
     */
    @Query("SELECT EXISTS(SELECT 1 FROM {entity_name.lower()}s WHERE id = :id)")
    suspend fun {entity_name.lower()}Exists(id: String): Boolean

    /**
     * Transaction example: Delete old and insert new {entity_name.lower()}s atomically
     * Ensures data consistency - all or nothing
     */
    @Transaction
    suspend fun refreshAll{entity_name}s({entity_name.lower()}s: List<{entity_name}Entity>) {{
        deleteAll{entity_name}s()
        insertAll{entity_name}s({entity_name.lower()}s)
    }}

    /**
     * Get {entity_name.lower()}s with pagination
     * Useful for large datasets to load incrementally
     */
    @Query("SELECT * FROM {entity_name.lower()}s ORDER BY createdAt DESC LIMIT :limit OFFSET :offset")
    suspend fun get{entity_name}sPaginated(limit: Int, offset: Int): List<{entity_name}Entity>
}}
"""

    def generate_room_entity_template(self, entity_name: str) -> str:
        """Generate a comprehensive Room Entity"""
        context = {
            "package_name": self.config.package_name,
            "entity_name": entity_name,
        }
        return self._render_template("templates/kotlin/room_entity.kt.template", context)

    def generate_room_database_template(self, entities: List[str]) -> str:
        """Generate Room Database configuration"""
        context = {
            "package_name": self.config.package_name,
            "entities": entities,
        }
        return self._render_template("templates/kotlin/room_database.kt.template", context)

    def generate_retrofit_api_template(self, entity_name: str) -> str:
        """Generate Retrofit API interface"""
        context = {
            "package_name": self.config.package_name,
            "entity_name": entity_name,
        }
        return self._render_template("templates/kotlin/retrofit_api.kt.template", context)

    def generate_dto_template(self, entity_name: str) -> str:
        """Generate Data Transfer Object (DTO)"""
        context = {
            "package_name": self.config.package_name,
            "entity_name": entity_name,
        }
        return self._render_template("templates/kotlin/dto.kt.template", context)

    def generate_domain_model_template(self, entity_name: str) -> str:
        """Generate Domain Model"""
        context = {
            "package_name": self.config.package_name,
            "entity_name": entity_name,
        }
        return self._render_template("templates/kotlin/domain_model.kt.template", context)

    def generate_use_case_template(self, entity_name: str, operation: str) -> str:
        """Generate Use Case following Clean Architecture"""
        context = {
            "package_name": self.config.package_name,
            "entity_name": entity_name,
            "operation": operation,
        }
        return self._render_template("templates/kotlin/use_case.kt.template", context)

    def generate_hilt_module_template(self, entity_name: str) -> str:
        """Generate Hilt Dependency Injection Module"""
        context = {
            "package_name": self.config.package_name,
            "entity_name": entity_name,
        }
        return self._render_template("templates/kotlin/hilt_module.kt.template", context)

    def generate_compose_screen_template(self, entity_name: str) -> str:
        """Generate Jetpack Compose Screen"""
        return f"""package {self.config.package_name}.presentation.{entity_name.lower()}

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import timber.log.Timber
import {self.config.package_name}.domain.model.{entity_name}
import {self.config.package_name}.util.UiEvent

/**
 * Main {entity_name} Screen using Jetpack Compose
 * 
 * Following Compose best practices:
 * - Stateless composable (state hoisted to ViewModel)
 * - collectAsStateWithLifecycle for lifecycle-aware state collection
 * - Proper side effect handling with LaunchedEffect
 * - Material 3 design components
 * - Accessibility support
 * 
 * @param viewModel The ViewModel providing state and handling actions
 * @param onNavigateToDetail Navigation callback for detail screen
 * @param onNavigateBack Navigation callback for back action
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun {entity_name}Screen(
    viewModel: {entity_name}ViewModel = hiltViewModel(),
    onNavigateToDetail: (String) -> Unit,
    onNavigateBack: () -> Unit
) {{
    // Collect state with lifecycle awareness
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val searchQuery by viewModel.searchQuery.collectAsStateWithLifecycle()
    
    // Snackbar host state for showing messages
    val snackbarHostState = remember {{ SnackbarHostState() }}
    
    // Handle one-time UI events
    LaunchedEffect(Unit) {{
        viewModel.uiEvent.collect {{ event ->
            when (event) {{
                is UiEvent.ShowSnackbar -> {{
                    snackbarHostState.showSnackbar(
                        message = event.message,
                        duration = SnackbarDuration.Short
                    )
                }}
                is UiEvent.Navigate -> {{
                    onNavigateToDetail(event.route)
                }}
                is UiEvent.NavigateBack -> {{
                    onNavigateBack()
                }}
            }}
        }}
    }}
    
    Scaffold(
        topBar = {{
            {entity_name}TopBar(
                searchQuery = searchQuery,
                onSearchQueryChange = {{ query ->
                    viewModel.onAction({entity_name}Action.Search(query))
                }},
                onNavigateBack = onNavigateBack
            )
        }},
        floatingActionButton = {{
            FloatingActionButton(
                onClick = {{ 
                    // Navigate to create screen or show dialog
                    Timber.d("Create new {entity_name.lower()}")
                }},
                containerColor = MaterialTheme.colorScheme.primary
            ) {{
                Icon(
                    imageVector = Icons.Default.Add,
                    contentDescription = "Create {entity_name}"
                )
            }}
        }},
        snackbarHost = {{ SnackbarHost(snackbarHostState) }}
    ) {{ paddingValues ->
        {entity_name}Content(
            uiState = uiState,
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            onAction = viewModel::onAction,
            onItemClick = {{ {entity_name.lower()} ->
                onNavigateToDetail({entity_name.lower()}.id)
            }}
        )
    }}
}}

/**
 * Top App Bar with search functionality
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun {entity_name}TopBar(
    searchQuery: String,
    onSearchQueryChange: (String) -> Unit,
    onNavigateBack: () -> Unit
) {{
    var isSearchActive by remember {{ mutableStateOf(false) }}
    
    TopAppBar(
        title = {{
            if (isSearchActive) {{
                TextField(
                    value = searchQuery,
                    onValueChange = onSearchQueryChange,
                    modifier = Modifier.fillMaxWidth(),
                    placeholder = {{ Text("Search {entity_name.lower()}s...") }},
                    singleLine = true,
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = MaterialTheme.colorScheme.surface,
                        unfocusedContainerColor = MaterialTheme.colorScheme.surface
                    )
                )
            }} else {{
                Text("{entity_name}s")
            }}
        }},
        navigationIcon = {{
            IconButton(onClick = onNavigateBack) {{
                Icon(
                    imageVector = Icons.Default.ArrowBack,
                    contentDescription = "Navigate back"
                )
            }}
        }},
        actions = {{
            IconButton(
                onClick = {{ 
                    isSearchActive = !isSearchActive
                    if (!isSearchActive) {{
                        onSearchQueryChange("")
                    }}
                }}
            ) {{
                Icon(
                    imageVector = if (isSearchActive) Icons.Default.Close else Icons.Default.Search,
                    contentDescription = if (isSearchActive) "Close search" else "Search"
                )
            }}
            IconButton(onClick = {{ /* Show filter options */ }}) {{
                Icon(
                    imageVector = Icons.Default.FilterList,
                    contentDescription = "Filter"
                )
            }}
        }},
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer,
            titleContentColor = MaterialTheme.colorScheme.onPrimaryContainer
        )
    )
}}

/**
 * Main content area
 */
@Composable
private fun {entity_name}Content(
    uiState: {entity_name}UiState,
    modifier: Modifier = Modifier,
    onAction: ({entity_name}Action) -> Unit,
    onItemClick: ({entity_name}) -> Unit
) {{
    Box(modifier = modifier) {{
        when {{
            uiState.isLoading && uiState.{entity_name.lower()}s.isEmpty() -> {{
                LoadingState(modifier = Modifier.align(Alignment.Center))
            }}
            uiState.error != null && uiState.{entity_name.lower()}s.isEmpty() -> {{
                ErrorState(
                    message = uiState.error,
                    onRetry = {{ onAction({entity_name}Action.Refresh) }},
                    modifier = Modifier.align(Alignment.Center)
                )
            }}
            uiState.{entity_name.lower()}s.isEmpty() -> {{
                EmptyState(modifier = Modifier.align(Alignment.Center))
            }}
            else -> {{
                {entity_name}List(
                    {entity_name.lower()}s = uiState.{entity_name.lower()}s,
                    onItemClick = onItemClick,
                    onDeleteClick = {{ {entity_name.lower()} ->
                        onAction({entity_name}Action.Delete({entity_name.lower()}.id))
                    }},
                    modifier = Modifier.fillMaxSize()
                )
            }}
        }}
        
        // Show loading indicator on top when refreshing
        if (uiState.isLoading && uiState.{entity_name.lower()}s.isNotEmpty()) {{
            LinearProgressIndicator(
                modifier = Modifier
                    .fillMaxWidth()
                    .align(Alignment.TopCenter)
            )
        }}
    }}
}}

/**
 * List of {entity_name.lower()}s
 */
@Composable
private fun {entity_name}List(
    {entity_name.lower()}s: List<{entity_name}>,
    onItemClick: ({entity_name}) -> Unit,
    onDeleteClick: ({entity_name}) -> Unit,
    modifier: Modifier = Modifier
) {{
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {{
        items(
            items = {entity_name.lower()}s,
            key = {{ it.id }}
        ) {{ {entity_name.lower()} ->
            {entity_name}Item(
                {entity_name.lower()} = {entity_name.lower()},
                onClick = {{ onItemClick({entity_name.lower()}) }},
                onDeleteClick = {{ onDeleteClick({entity_name.lower()}) }}
            )
        }}
    }}
}}

/**
 * Individual {entity_name.lower()} item card
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun {entity_name}Item(
    {entity_name.lower()}: {entity_name},
    onClick: () -> Unit,
    onDeleteClick: () -> Unit,
    modifier: Modifier = Modifier
) {{
    var showDeleteDialog by remember {{ mutableStateOf(false) }}
    
    Card(
        onClick = onClick,
        modifier = modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {{
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {{
            Column(modifier = Modifier.weight(1f)) {{
                Text(
                    text = {entity_name.lower()}.name,
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                
                {entity_name.lower()}.description?.let {{ description ->
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = description,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                }}
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {{
                    AssistChip(
                        onClick = {{}},
                        label = {{ Text({entity_name.lower()}.status.name) }},
                        leadingIcon = {{
                            Icon(
                                imageVector = Icons.Default.Info,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp)
                            )
                        }}
                    )
                }}
            }}
            
            IconButton(onClick = {{ showDeleteDialog = true }}) {{
                Icon(
                    imageVector = Icons.Default.Delete,
                    contentDescription = "Delete {entity_name.lower()}",
                    tint = MaterialTheme.colorScheme.error
                )
            }}
        }}
    }}
    
    if (showDeleteDialog) {{
        DeleteConfirmationDialog(
            {entity_name.lower()}Name = {entity_name.lower()}.name,
            onConfirm = {{
                showDeleteDialog = false
                onDeleteClick()
            }},
            onDismiss = {{ showDeleteDialog = false }}
        )
    }}
}}

/**
 * Loading state
 */
@Composable
private fun LoadingState(modifier: Modifier = Modifier) {{
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {{
        CircularProgressIndicator()
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "Loading {entity_name.lower()}s...",
            style = MaterialTheme.typography.bodyLarge
        )
    }}
}}

/**
 * Error state
 */
@Composable
private fun ErrorState(
    message: String,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier
) {{
    Column(
        modifier = modifier.padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {{
        Icon(
            imageVector = Icons.Default.Error,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.error
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "Error",
            style = MaterialTheme.typography.titleLarge
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(16.dp))
        Button(onClick = onRetry) {{
            Icon(imageVector = Icons.Default.Refresh, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Retry")
        }}
    }}
}}

/**
 * Empty state
 */
@Composable
private fun EmptyState(modifier: Modifier = Modifier) {{
    Column(
        modifier = modifier.padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {{
        Icon(
            imageVector = Icons.Default.Info,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "No {entity_name.lower()}s yet",
            style = MaterialTheme.typography.titleLarge
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "Tap the + button to create your first {entity_name.lower()}",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }}
}}

/**
 * Delete confirmation dialog
 */
@Composable
private fun DeleteConfirmationDialog(
    {entity_name.lower()}Name: String,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit
) {{
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = {{
            Icon(
                imageVector = Icons.Default.Warning,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.error
            )
        }},
        title = {{ Text("Delete {entity_name}?") }},
        text = {{
            Text("Are you sure you want to delete \\"${{{entity_name.lower()}Name}}\\"? This action cannot be undone.")
        }},
        confirmButton = {{
            TextButton(
                onClick = onConfirm,
                colors = ButtonDefaults.textButtonColors(
                    contentColor = MaterialTheme.colorScheme.error
                )
            ) {{
                Text("Delete")
            }}
        }},
        dismissButton = {{
            TextButton(onClick = onDismiss) {{
                Text("Cancel")
            }}
        }}
    )
}}
"""

    def generate_unit_test_template(self, entity_name: str) -> str:
        """Generate comprehensive unit tests"""
        return f"""package {self.config.package_name}.presentation.{entity_name.lower()}

import androidx.arch.core.executor.testing.InstantTaskExecutorRule
import app.cash.turbine.test
import com.google.common.truth.Truth.assertThat
import io.mockk.*
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.test.*
import org.junit.After
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import {self.config.package_name}.domain.model.{entity_name}
import {self.config.package_name}.domain.usecase.*
import {self.config.package_name}.util.Resource
import {self.config.package_name}.util.UiEvent

/**
 * Unit tests for {entity_name}ViewModel
 * 
 * Testing Strategy:
 * - Use MockK for mocking dependencies
 * - Test coroutines with TestDispatcher
 * - Use Turbine for Flow testing
 * - Follow Given-When-Then pattern
 * - Test happy paths and error cases
 * - Verify UI state transitions
 * 
 * Test Coverage:
 * - Initial state
 * - Loading states
 * - Success scenarios
 * - Error handling
 * - User actions
 * - State updates
 */
@OptIn(ExperimentalCoroutinesApi::class)
class {entity_name}ViewModelTest {{

    // Rule to execute LiveData operations synchronously
    @get:Rule
    val instantTaskExecutorRule = InstantTaskExecutorRule()

    // Test dispatcher for coroutines
    private val testDispatcher = StandardTestDispatcher()

    // Mocked dependencies
    private lateinit var get{entity_name}sUseCase: Get{entity_name}sUseCase
    private lateinit var create{entity_name}UseCase: Create{entity_name}UseCase
    private lateinit var update{entity_name}UseCase: Update{entity_name}UseCase
    private lateinit var delete{entity_name}UseCase: Delete{entity_name}UseCase

    // System under test
    private lateinit var viewModel: {entity_name}ViewModel

    // Test data
    private val test{entity_name} = {entity_name}.sample()
    private val test{entity_name}List = listOf(
        {entity_name}.sample().copy(id = "1", name = "Test 1"),
        {entity_name}.sample().copy(id = "2", name = "Test 2"),
        {entity_name}.sample().copy(id = "3", name = "Test 3")
    )

    @Before
    fun setup() {{
        // Set main dispatcher for testing
        Dispatchers.setMain(testDispatcher)

        // Initialize mocks
        get{entity_name}sUseCase = mockk()
        create{entity_name}UseCase = mockk()
        update{entity_name}UseCase = mockk()
        delete{entity_name}UseCase = mockk()

        // Create ViewModel with mocked dependencies
        viewModel = {entity_name}ViewModel(
            get{entity_name}sUseCase = get{entity_name}sUseCase,
            create{entity_name}UseCase = create{entity_name}UseCase,
            update{entity_name}UseCase = update{entity_name}UseCase,
            delete{entity_name}UseCase = delete{entity_name}UseCase
        )
    }}

    @After
    fun tearDown() {{
        Dispatchers.resetMain()
        clearAllMocks()
    }}

    @Test
    fun `initial state is correct`() = runTest {{
        // Given - ViewModel is created

        // When - Check initial state
        val initialState = viewModel.uiState.value

        // Then - State should be empty and not loading
        assertThat(initialState.{entity_name.lower()}s).isEmpty()
        assertThat(initialState.selected{entity_name}).isNull()
        assertThat(initialState.isLoading).isFalse()
        assertThat(initialState.error).isNull()
    }}

    @Test
    fun `load {entity_name.lower()}s successfully updates state`() = runTest {{
        // Given - Use case returns success
        coEvery {{ get{entity_name}sUseCase() }} returns flow {{
            emit(Resource.Loading())
            emit(Resource.Success(test{entity_name}List))
        }}

        // When - Load {entity_name.lower()}s
        viewModel.load{entity_name}s()
        advanceUntilIdle()

        // Then - State should contain {entity_name.lower()}s and not be loading
        val finalState = viewModel.uiState.value
        assertThat(finalState.{entity_name.lower()}s).isEqualTo(test{entity_name}List)
        assertThat(finalState.isLoading).isFalse()
        assertThat(finalState.error).isNull()
    }}

    @Test
    fun `load {entity_name.lower()}s with error updates state correctly`() = runTest {{
        // Given - Use case returns error
        val errorMessage = "Network error"
        coEvery {{ get{entity_name}sUseCase() }} returns flow {{
            emit(Resource.Loading())
            emit(Resource.Error(errorMessage))
        }}

        // When - Load {entity_name.lower()}s
        viewModel.load{entity_name}s()
        advanceUntilIdle()

        // Then - State should show error
        val finalState = viewModel.uiState.value
        assertThat(finalState.isLoading).isFalse()
        assertThat(finalState.error).isEqualTo(errorMessage)
    }}

    @Test
    fun `create {entity_name.lower()} action calls use case`() = runTest {{
        // Given - Use case returns success
        coEvery {{ create{entity_name}UseCase(test{entity_name}) }} returns flow {{
            emit(Resource.Success(test{entity_name}))
        }}
        coEvery {{ get{entity_name}sUseCase() }} returns flow {{
            emit(Resource.Success(test{entity_name}List))
        }}

        // When - Create action is triggered
        viewModel.onAction({entity_name}Action.Create(test{entity_name}))
        advanceUntilIdle()

        // Then - Use case should be called
        coVerify {{ create{entity_name}UseCase(test{entity_name}) }}
    }}

    @Test
    fun `delete {entity_name.lower()} action calls use case and shows snackbar`() = runTest {{
        // Given - Use case returns success
        coEvery {{ delete{entity_name}UseCase(test{entity_name}.id) }} returns flow {{
            emit(Resource.Success(Unit))
        }}
        coEvery {{ get{entity_name}sUseCase() }} returns flow {{
            emit(Resource.Success(test{entity_name}List))
        }}

        // When - Delete action is triggered
        viewModel.uiEvent.test {{
            viewModel.onAction({entity_name}Action.Delete(test{entity_name}.id))
            advanceUntilIdle()

            // Then - Should emit snackbar event
            val event = awaitItem()
            assertThat(event).isInstanceOf(UiEvent.ShowSnackbar::class.java)
            assertThat((event as UiEvent.ShowSnackbar).message).contains("deleted")
        }}

        // And - Use case should be called
        coVerify {{ delete{entity_name}UseCase(test{entity_name}.id) }}
    }}

    @Test
    fun `search action updates search query`() = runTest {{
        // Given - Initial search query is empty
        val searchQuery = "test query"

        // When - Search action is triggered
        viewModel.onAction({entity_name}Action.Search(searchQuery))
        advanceUntilIdle()

        // Then - Search query should be updated
        assertThat(viewModel.searchQuery.value).isEqualTo(searchQuery)
    }}

    @Test
    fun `refresh action reloads {entity_name.lower()}s`() = runTest {{
        // Given - Use case returns success
        coEvery {{ get{entity_name}sUseCase() }} returns flow {{
            emit(Resource.Success(test{entity_name}List))
        }}

        // When - Refresh action is triggered
        viewModel.onAction({entity_name}Action.Refresh)
        advanceUntilIdle()

        // Then - Use case should be called
        coVerify {{ get{entity_name}sUseCase() }}
    }}

    @Test
    fun `select {entity_name.lower()} action updates selected {entity_name.lower()} in state`() = runTest {{
        // Given - Initial selected {entity_name.lower()} is null

        // When - Select action is triggered
        viewModel.onAction({entity_name}Action.Select(test{entity_name}))
        advanceUntilIdle()

        // Then - Selected {entity_name.lower()} should be updated
        assertThat(viewModel.uiState.value.selected{entity_name}).isEqualTo(test{entity_name})
    }}

    @Test
    fun `clear error action removes error from state`() = runTest {{
        // Given - State has an error
        coEvery {{ get{entity_name}sUseCase() }} returns flow {{
            emit(Resource.Error("Test error"))
        }}
        viewModel.load{entity_name}s()
        advanceUntilIdle()

        // When - Clear error action is triggered
        viewModel.onAction({entity_name}Action.ClearError)
        advanceUntilIdle()

        // Then - Error should be null
        assertThat(viewModel.uiState.value.error).isNull()
    }}

    @Test
    fun `loading state is set during async operations`() = runTest {{
        // Given - Use case has delay
        coEvery {{ get{entity_name}sUseCase() }} returns flow {{
            emit(Resource.Loading())
            // Simulate network delay
        }}

        // When - Load {entity_name.lower()}s
        viewModel.load{entity_name}s()
        
        // Don't advance time yet
        // Then - Loading should be true
        assertThat(viewModel.uiState.value.isLoading).isTrue()
    }}
}}
"""

    def generate_util_classes(self) -> str:
        """Generate utility classes (Resource, NetworkMonitor, etc.)"""
        return f"""package {self.config.package_name}.util

import kotlinx.coroutines.flow.Flow

/**
 * Generic wrapper for data with loading, success, and error states
 * 
 * Usage:
 * - Resource.Loading: Operation in progress
 * - Resource.Success: Operation completed successfully with data
 * - Resource.Error: Operation failed with error message
 * 
 * Benefits:
 * - Type-safe state management
 * - Consistent error handling
 * - Reactive UI updates
 */
sealed class Resource<T>(
    val data: T? = null,
    val message: String? = null
) {{
    class Success<T>(data: T) : Resource<T>(data)
    class Error<T>(message: String, data: T? = null) : Resource<T>(data, message)
    class Loading<T>(data: T? = null) : Resource<T>(data)

    /**
     * Check if resource is successful
     */
    fun isSuccess(): Boolean = this is Success

    /**
     * Check if resource is error
     */
    fun isError(): Boolean = this is Error

    /**
     * Check if resource is loading
     */
    fun isLoading(): Boolean = this is Loading

    /**
     * Get data or null
     */
    fun getDataOrNull(): T? = data

    /**
     * Get data or throw exception
     */
    fun getDataOrThrow(): T {{
        return data ?: throw IllegalStateException("Data is null")
    }}
}}

/**
 * UI Event for one-time events (navigation, snackbar, etc.)
 */
sealed class UiEvent {{
    data class ShowSnackbar(val message: String) : UiEvent()
    data class Navigate(val route: String) : UiEvent()
    object NavigateBack : UiEvent()
    data class ShowDialog(val title: String, val message: String) : UiEvent()
}}

/**
 * Network Monitor interface
 */
interface NetworkMonitor {{
    fun isNetworkAvailable(): Boolean
    fun observeNetworkStatus(): Flow<Boolean>
}}

/**
 * Network Monitor implementation
 */
class NetworkMonitorImpl(
    private val context: android.content.Context
) : NetworkMonitor {{
    
    private val connectivityManager = context.getSystemService(
        android.content.Context.CONNECTIVITY_SERVICE
    ) as android.net.ConnectivityManager

    override fun isNetworkAvailable(): Boolean {{
        val network = connectivityManager.activeNetwork ?: return false
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
        
        return capabilities.hasCapability(
            android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET
        ) && capabilities.hasCapability(
            android.net.NetworkCapabilities.NET_CAPABILITY_VALIDATED
        )
    }}

    override fun observeNetworkStatus(): Flow<Boolean> = kotlinx.coroutines.flow.callbackFlow {{
        val callback = object : android.net.ConnectivityManager.NetworkCallback() {{
            override fun onAvailable(network: android.net.Network) {{
                trySend(true)
            }}

            override fun onLost(network: android.net.Network) {{
                trySend(false)
            }}
        }}

        connectivityManager.registerDefaultNetworkCallback(callback)

        awaitClose {{
            connectivityManager.unregisterNetworkCallback(callback)
        }}
    }}
}}

/**
 * Extension functions for