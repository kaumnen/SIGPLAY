# Implementation Plan

- [x] 1. Set up project structure and data models
  - Create directory structure for views, widgets, styles, and models
  - Define Track dataclass for placeholder music data
  - Define ViewState enum for managing view states
  - _Requirements: 1.1, 2.1, 4.1_

- [x] 2. Create custom CSS theme file
  - Create app.tcss file with retro-modern orange color palette
  - Define global styles for Screen background
  - Define styles for header, footer, and view containers
  - Define selection and highlight styles with orange accents
  - Define list item and hover states
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 1.3_

- [x] 3. Implement Header widget with ASCII art
  - Create header.py with Header widget class extending Static
  - Define SIGPLAY ASCII art as multi-line string constant
  - Implement compose method to display ASCII art
  - Apply CSS styling with orange color scheme
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 4. Implement LibraryView with vim navigation
  - Create library.py with LibraryView widget class
  - Use Textual's built-in ListView and ListItem widgets
  - Generate placeholder track data (5-10 sample tracks)
  - Implement key event handlers for j/k vim navigation
  - Map j/k keys to ListView's cursor_down/cursor_up actions
  - Apply CSS styling for selection highlighting
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 2.3_

- [x] 5. Implement NowPlayingView with track info display
  - Create now_playing.py with NowPlayingView widget class
  - Use Container widget with nested Static widgets for layout
  - Use built-in ProgressBar widget for playback progress
  - Display placeholder track information (title, artist, album)
  - Display placeholder progress bar with sample time values
  - Apply CSS styling consistent with theme
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 6. Implement VisualizerView with animated placeholder
  - Create visualizer.py with VisualizerView widget class
  - Use Static widget for displaying visualization content
  - Implement set_interval for periodic animation updates
  - Create placeholder ASCII bar pattern or waveform animation
  - Update visualization content every 100-200ms
  - Apply orange color gradient styling via CSS
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 7. Implement main SigplayApp with view switching
  - Update main.py with SigplayApp class extending Textual App
  - Load and apply custom CSS theme from app.tcss
  - Implement compose method with Header, ContentSwitcher, and Footer
  - Add LibraryView, NowPlayingView, and VisualizerView to ContentSwitcher
  - Implement on_mount to set default view to Library
  - Define keybinding for 'q' key to quit application
  - Define keybinding for Tab key to cycle through views
  - Implement action_quit method for clean shutdown
  - Implement action_cycle_view method to switch between views
  - Update Footer to display current view and keyboard shortcuts
  - _Requirements: 1.1, 1.2, 1.4, 2.1, 2.2, 2.4, 2.5, 3.1, 3.2, 3.3_

- [ ] 8. Integrate all components and test application
  - Wire up all imports in __init__.py files
  - Verify all views are accessible via Tab navigation
  - Test vim navigation (j/k) in Library view
  - Test quit functionality with 'q' key
  - Verify ASCII art displays correctly in header
  - Verify color scheme renders properly across all views
  - Test visualizer animation runs smoothly
  - Verify footer updates with current view information
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3_
