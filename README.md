## Overview

This application is designed to handle file uploads, process data, and generate reports through interaction with the Trustty Reporter API. It employs a layered architecture to separate concerns and manage complexity. The application also utilizes Celery for scalability and Redis for efficient session handling and report caching.

## Key Components

1. **Flask Application**: The core of the web application, built using the Flask framework.
2. **Flask-Login**: Handles user authentication and session management.
3. **Trustty Reporter API**: Provides specialized data processing and report generation capabilities.
4. **Celery Message Queue**: Acts as middleware between Flask frontend and FastAPI LangServe (Trustty Reporter API), enabling asynchronous task processing and horizontal scalability with load balancing.
5. **Server-Sent Events**: Used in Celery server to stream real-time updates back to the Flask frontend.
6. **Redis Cache**: Manages session data and caches generated reports for improved performance.

## Architecture 1

The application follows a layered architecture:

1. **Presentation Layer**: Handles user interface and interactions.
2. **Application Layer**: Manages routing, sessions, and authentication.
3. **Service Layer**: Coordinates file processing, data analysis, and report generation.
4. **Data Access Layer**: Interacts with Trustty Reporter API and manages temporary file storage.
5. **Caching Layer**: Utilizes Redis for session management and report caching.
6. **External Services**: The Trustty Reporter API for advanced processing tasks.

<img width="980" height="2459" alt="diagram-export-24-10-2025-16_32_13" src="https://github.com/user-attachments/assets/b1fd22d3-7b8f-489a-a486-241d81048f40" />

## Architecture 2 (More scalable)

The more scalable solution is to add a message queue between the the application layer and the service layer to ensure horizontal scaling with a load balancer.

<img width="269" height="592" alt="image" src="https://github.com/user-attachments/assets/181d9eed-bbb6-40b4-92b0-c9adb72b3446" />


## Key Features

### File Upload and Processing

- Supports multiple file uploads.
- Handles various file formats (CSV, Excel).
- Converts Excel files to CSV for uniform processing.
- Ensures proper encoding of CSV files (UTF-8).

### Data Analysis and Report Generation

- Interacts with Trustty Reporter API for specialized data preprocessing and analysis.
- Generates summaries for uploaded documents and CSV files.
- Creates detailed reports based on processed data.
- Caches generated reports in Redis for quick retrieval.

### Real-time Updates

- Utilizes Celery message queue for asynchronous task processing between Flask frontend and FastAPI LangServe backend.
- Employs Server-Sent Events in Celery server to stream real-time updates back to the Flask frontend.
- Provides a responsive user experience during long-running tasks with live progress updates.

### Report Editing and Regeneration

- Allows users to edit generated reports.
- Supports regeneration of HTML reports based on edited content.
- Caches updated reports for efficient access.

### Session Management

- Uses Redis to store session data, enabling better scalability and performance.
- Allows for distributed session management in a multi-server environment.

## Security Considerations

- Uses Flask-Login for user authentication.
- Implements API key authentication for Trustty Reporter API requests.
- Employs secure file naming and temporary storage for uploaded files.
- Utilizes Redis for secure, centralized session storage.

## Performance Optimizations

- Redis caching significantly reduces load times for previously generated reports.
- Session data in Redis allows for faster session retrieval and improved application responsiveness.
- Distributed caching enables better load balancing and scalability.
- Celery message queue enables asynchronous task processing and horizontal scalability with load balancing between Flask frontend and FastAPI LangServe backend.

## Future Improvements

1. Implement additional error handling and user feedback mechanisms.
2. Add support for additional file formats and data sources.
3. Enhance the report editing interface for a better user experience.
4. Implement more granular caching strategies to optimize Redis usage.
5. Add unit and integration tests to ensure reliability.
6. Develop a cache invalidation strategy for updating stale report data.
7. Explore advanced features of the Trustty Reporter API to enhance report generation capabilities.
