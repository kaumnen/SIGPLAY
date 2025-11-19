# Implementation Plan

- [x] 1. Set up project structure and dependencies
  - Add pedalboard, hypothesis, and strands-agents to pyproject.toml
  - Create directory structure for new widgets and services
  - Set up basic imports and module structure
  - _Requirements: All_

- [x] 2. Create data models
- [x] 2.1 Implement MixRequest model
  - Create models/mix_request.py with MixRequest dataclass
  - Include fields for tracks, instructions, and output directory
  - Add validation methods
  - _Requirements: 5.1_

- [x] 3. Build Floppy Mix dialog UI components
- [x] 3.1 Create FloppyMixDialog widget
  - Implement modal dialog container in widgets/floppy_mix_dialog.py
  - Add reactive state management (is_visible, mixing_state)
  - Implement show/hide methods
  - Handle keyboard events (Escape, Enter, 'd' key)
  - _Requirements: 1.1, 1.3, 4.1_

- [x] 3.2 Create TrackSelectionPanel widget
  - Implement track list display with ListView
  - Add vim-style navigation (j/k keys)
  - Implement Space key toggle for selection
  - Display visual indicators for selected tracks
  - Maintain selected_tracks reactive state
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3.3 Create InstructionsPanel widget
  - Implement multi-line TextArea for instructions
  - Add placeholder text with examples
  - Implement text validation
  - Add clear() method
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3.4 Create MixProgressPanel widget
  - Implement status message display
  - Add LoadingIndicator for progress
  - Create save/discard buttons
  - Implement show/hide controls methods
  - _Requirements: 4.2, 7.3, 8.1, 9.1, 10.1, 10.2, 10.3_

- [x] 3.5 Wire up dialog components
  - Compose all panels in FloppyMixDialog
  - Connect panel interactions to dialog state
  - Implement validation before starting mix
  - Add error notification display
  - _Requirements: 4.4, 4.5_

- [x] 4. Implement Strands Agents DJ agent
- [x] 4.1 Create DJ agent script
  - Create floppy_mix_agent.py with Strands Agent configuration
  - Configure AWS Bedrock model (Claude)
  - Write system prompt for DJ/audio engineer persona
  - Set up Python execution tools
  - Add file system access capabilities
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 4.2 Implement agent mixing logic
  - Write agent code to interpret natural language instructions
  - Generate structured mixing plans
  - Implement Pedalboard code generation
  - Add error handling and logging
  - Return mix file path on completion
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ]* 4.3 Write property test for agent request completeness
  - **Property 9: Agent request completeness**
  - **Validates: Requirements 5.1, 5.2**

- [ ]* 4.4 Write property test for agent response validity
  - **Property 10: Agent response validity**
  - **Validates: Requirements 5.3**

- [x] 5. Create DJAgentClient service
- [x] 5.1 Implement agent invocation
  - Create services/dj_agent_client.py
  - Implement create_mix() method with subprocess management
  - Prepare agent input data (tracks + instructions)
  - Set up agent process with timeout (5 minutes)
  - _Requirements: 5.1, 5.4_

- [x] 5.2 Implement progress monitoring
  - Stream agent output to progress callback
  - Parse agent status messages
  - Handle agent completion and errors
  - Cleanup agent process on completion/timeout
  - _Requirements: 10.2_

- [x] 5.3 Add error handling
  - Handle agent startup failures
  - Handle agent timeouts
  - Handle invalid responses
  - Provide user-friendly error messages
  - _Requirements: 5.4, 5.5_

- [ ]* 5.4 Write unit tests for DJAgentClient
  - Test agent invocation with mock agent
  - Test progress streaming
  - Test timeout handling
  - Test error scenarios
  - _Requirements: 5.1, 5.4, 5.5_

- [x] 6. Integrate audio playback
- [x] 6.1 Implement mix preview
  - Load generated mix file into AudioPlayer
  - Start playback automatically
  - Display playback controls in dialog
  - Handle Space key for play/pause
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 6.2 Implement cleanup on dialog close
  - Stop playback when dialog closes
  - Delete temporary mix file if not saved
  - Reset dialog state
  - _Requirements: 7.5, 9.4_

- [ ]* 6.3 Write property test for automatic preview playback
  - **Property 15: Automatic preview playback**
  - **Validates: Requirements 7.1, 7.2**

- [ ]* 6.4 Write property test for playback control responsiveness
  - **Property 16: Playback control responsiveness**
  - **Validates: Requirements 7.4**

- [ ]* 6.5 Write property test for dialog closure cleanup
  - **Property 17: Dialog closure cleanup**
  - **Validates: Requirements 7.5, 9.4**

- [ ] 7. Implement save/discard functionality
- [ ] 7.1 Implement save mix
  - Prompt user for filename
  - Validate filename
  - Copy mix file to Music Library directory
  - Display success notification
  - Handle save errors
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 7.2 Implement discard mix
  - Stop playback
  - Delete temporary mix file
  - Reset dialog to initial state
  - Clear selections and instructions
  - _Requirements: 9.1, 9.2, 9.3_

- [ ]* 7.3 Write property test for save operation correctness
  - **Property 18: Save operation correctness**
  - **Validates: Requirements 8.3**

- [ ]* 7.4 Write property test for discard operation cleanup
  - **Property 19: Discard operation cleanup**
  - **Validates: Requirements 9.2, 9.3**

- [ ] 8. Add dialog to main application
- [ ] 8.1 Integrate FloppyMixDialog into SigplayApp
  - Add FloppyMixDialog to main app composition
  - Bind 'd' key to show dialog
  - Pass AudioPlayer and MusicLibrary services
  - Ensure dialog doesn't interrupt playback
  - _Requirements: 1.1, 1.2, 1.4_

- [ ]* 8.2 Write property test for dialog maintains playback state
  - **Property 1: Dialog maintains playback state**
  - **Validates: Requirements 1.2**

- [ ] 9. Implement UI property tests
- [ ]* 9.1 Write property test for track list completeness
  - **Property 2: Track list completeness**
  - **Validates: Requirements 2.1**

- [ ]* 9.2 Write property test for navigation cursor movement
  - **Property 3: Navigation cursor movement**
  - **Validates: Requirements 2.2**

- [ ]* 9.3 Write property test for selection toggle idempotence
  - **Property 4: Selection toggle idempotence**
  - **Validates: Requirements 2.3**

- [ ]* 9.4 Write property test for selection state persistence
  - **Property 5: Selection state persistence**
  - **Validates: Requirements 2.4, 2.5**

- [ ]* 9.5 Write property test for text input preservation
  - **Property 6: Text input preservation**
  - **Validates: Requirements 3.2, 3.4**

- [ ]* 9.6 Write property test for mixing initiation preconditions
  - **Property 7: Mixing initiation preconditions**
  - **Validates: Requirements 4.1**

- [ ]* 9.7 Write property test for UI lock during processing
  - **Property 8: UI lock during processing**
  - **Validates: Requirements 4.3**

- [ ] 10. Implement audio processing property tests
- [ ]* 10.1 Write property test for audio file loading completeness
  - **Property 11: Audio file loading completeness**
  - **Validates: Requirements 6.1**

- [ ]* 10.2 Write property test for tempo adjustment pitch preservation
  - **Property 12: Tempo adjustment pitch preservation**
  - **Validates: Requirements 6.2**

- [ ]* 10.3 Write property test for gapless transition property
  - **Property 13: Gapless transition property**
  - **Validates: Requirements 6.4**

- [ ]* 10.4 Write property test for mix file generation
  - **Property 14: Mix file generation**
  - **Validates: Requirements 6.5**

- [ ] 11. Implement error handling property tests
- [ ]* 11.1 Write property test for error logging and notification
  - **Property 20: Error logging and notification**
  - **Validates: Requirements 10.4, 10.5**

- [ ]* 11.2 Write property test for status message accuracy
  - **Property 21: Status message accuracy**
  - **Validates: Requirements 10.2**

- [ ] 12. Add styling
- [ ] 12.1 Create Floppy Mix dialog styles
  - Add styles to styles/app.tcss for all dialog components
  - Use retro orange color palette
  - Style track selection indicators
  - Style progress indicators and buttons
  - Ensure responsive layout
  - _Requirements: All UI requirements_

- [ ] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
