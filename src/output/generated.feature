# Auto-generated Gherkin scenarios
# Generated: 2025-12-07 20:12:51

Feature: Validate "Learn More" Pop-Up Functionality on Patient Stories Page

  Background:
    Given the user navigates to "https://www.tivdak.com/patient-stories/"

  Scenario: Canceling the "Learn More" pop-up
    When the user clicks the "Learn More" button
    Then a pop-up should appear with the title "You are now leaving tivdak.com"
    When the user clicks the "cancel" button
    Then the pop-up should close
    When the user clicks the "Learn More" button again
    Then a pop-up should appear with the title "You are now leaving tivdak.com"

  Scenario: Continuing through the "Learn More" pop-up
    Given the user has already opened the "Learn More" pop-up
    When the user clicks the "continue" button on the pop-up
    Then the URL should change to "https://alishasjourney.com/"