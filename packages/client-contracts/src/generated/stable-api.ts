// Generated from registered FastAPI routes. Do not edit.
// schema-sha256: 7c4761b1b09ec04170393985e5bda55e1d91dd668096d3414d2ef2f53720071c
export interface paths {
    "/api/ai/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Ai Status */
        get: operations["ai_status_api_ai_status_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/ask": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Ask */
        post: operations["ask_api_ask_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout_api_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Me */
        get: operations["me_api_auth_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create User */
        post: operations["create_user_api_auth_users_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/province-documents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Province Documents */
        get: operations["list_province_documents_api_province_documents_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/province-documents/{slug}/application/generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Generate Province Application */
        post: operations["generate_province_application_api_province_documents__slug__application_generate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/province-documents/{slug}/evidence/generate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Generate Province Evidence */
        post: operations["generate_province_evidence_api_province_documents__slug__evidence_generate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AIStatusResponse */
        AIStatusResponse: {
            /** Local Model Started */
            local_model_started: boolean;
            /** Message */
            message?: string | null;
            /** Model */
            model: string;
            /** Provider */
            provider: string;
            /** Ready */
            ready: boolean;
            /** Status */
            status?: string | null;
            /** Transport */
            transport?: string | null;
        } & {
            [key: string]: unknown;
        };
        /** ApplicationRequest */
        ApplicationRequest: {
            /**
             * Acceptmediation
             * @default
             */
            acceptMediation?: string;
            /**
             * Actualofficeaddress
             * @default
             */
            actualOfficeAddress?: string;
            /**
             * Age
             * @default
             */
            age?: string;
            /**
             * Applicantmailingaddress
             * @default
             */
            applicantMailingAddress?: string;
            /**
             * Applicantname
             * @default
             */
            applicantName?: string;
            /**
             * Applicantpostalcode
             * @default
             */
            applicantPostalCode?: string;
            /**
             * Applicantworkunit
             * @default
             */
            applicantWorkUnit?: string;
            /**
             * Applicationdate
             * @default
             */
            applicationDate?: string;
            /**
             * Attendancemethod
             * @default
             */
            attendanceMethod?: string;
            /**
             * Attendancerequired
             * @default
             */
            attendanceRequired?: string;
            /**
             * Averagemonthlysalary
             * @default
             */
            averageMonthlySalary?: string;
            /**
             * Birthdate
             * @default
             */
            birthDate?: string;
            /**
             * Claimcalculation
             * @default
             */
            claimCalculation?: string;
            /**
             * Committeename
             * @default
             */
            committeeName?: string;
            /**
             * Companycontact
             * @default
             */
            companyContact?: string;
            /**
             * Companycontactphone
             * @default
             */
            companyContactPhone?: string;
            /**
             * Contractenddate
             * @default
             */
            contractEndDate?: string;
            /**
             * Contractstartdate
             * @default
             */
            contractStartDate?: string;
            /**
             * Copycount
             * @default 1
             */
            copyCount?: number;
            /**
             * Currentaddress
             * @default
             */
            currentAddress?: string;
            /**
             * Currentlyemployed
             * @default
             */
            currentlyEmployed?: string;
            /**
             * Departmenthead
             * @default
             */
            departmentHead?: string;
            /**
             * Departmentheadposition
             * @default
             */
            departmentHeadPosition?: string;
            /**
             * Departuredate
             * @default
             */
            departureDate?: string;
            /**
             * Departurereason
             * @default
             */
            departureReason?: string;
            /**
             * Employmentdate
             * @default
             */
            employmentDate?: string;
            /**
             * Employmenttype
             * @default
             */
            employmentType?: string;
            /**
             * Factsreason
             * @default
             */
            factsReason?: string;
            /**
             * Gender
             * @default
             */
            gender?: string;
            /**
             * Householdtype
             * @default
             */
            householdType?: string;
            /**
             * Idaddress
             * @default
             */
            idAddress?: string;
            /**
             * Identitydocumenttype
             * @default
             */
            identityDocumentType?: string;
            /**
             * Idnumber
             * @default
             */
            idNumber?: string;
            /**
             * Jobtitle
             * @default
             */
            jobTitle?: string;
            /**
             * Lastworkingdate
             * @default
             */
            lastWorkingDate?: string;
            /**
             * Legalaid
             * @default
             */
            legalAid?: string;
            /**
             * Legalrepname
             * @default
             */
            legalRepName?: string;
            /**
             * Legalrepphone
             * @default
             */
            legalRepPhone?: string;
            /**
             * Legalrepposition
             * @default
             */
            legalRepPosition?: string;
            /**
             * Mailingaddress
             * @default
             */
            mailingAddress?: string;
            /**
             * Nationality
             * @default
             */
            nationality?: string;
            /**
             * Nativeplace
             * @default
             */
            nativePlace?: string;
            /**
             * Occupation
             * @default
             */
            occupation?: string;
            /**
             * Officeatregisteredaddress
             * @default
             */
            officeAtRegisteredAddress?: string;
            /**
             * Otherdocumentnumber
             * @default
             */
            otherDocumentNumber?: string;
            /**
             * Otherdocumenttype
             * @default
             */
            otherDocumentType?: string;
            /**
             * Othernotes
             * @default
             */
            otherNotes?: string;
            /**
             * Phone
             * @default
             */
            phone?: string;
            /**
             * Registeredaddress
             * @default
             */
            registeredAddress?: string;
            /**
             * Registeredcapital
             * @default
             */
            registeredCapital?: string;
            /** Requests */
            requests?: string[];
            /**
             * Respondentname
             * @default
             */
            respondentName?: string;
            /**
             * Respondentpostalcode
             * @default
             */
            respondentPostalCode?: string;
            /**
             * Respondenttype
             * @default
             */
            respondentType?: string;
            /**
             * Salaryadjustments
             * @default
             */
            salaryAdjustments?: string;
            /**
             * Salarypaymentmethod
             * @default
             */
            salaryPaymentMethod?: string;
            /**
             * Salaryreceiptrequired
             * @default
             */
            salaryReceiptRequired?: string;
            /**
             * Signedcontract
             * @default
             */
            signedContract?: string;
            /**
             * Socialcreditcode
             * @default
             */
            socialCreditCode?: string;
            /**
             * Startingsalary
             * @default
             */
            startingSalary?: string;
            /**
             * Workaddress
             * @default
             */
            workAddress?: string;
            /**
             * Workschedule
             * @default
             */
            workSchedule?: string;
        };
        /** ChatMessage */
        ChatMessage: {
            /** Content */
            content: string;
            /**
             * Role
             * @enum {string}
             */
            role: "user" | "assistant";
        };
        /** CreateUserRequest */
        CreateUserRequest: {
            /** Password */
            password: string;
            /**
             * Role
             * @default user
             * @enum {string}
             */
            role?: "user" | "admin";
            /** Username */
            username: string;
        };
        /** DocumentFieldDefinition */
        DocumentFieldDefinition: {
            /** Label */
            label: string;
            /** Maxlength */
            maxLength: number;
            /** Options */
            options?: string[];
            /**
             * Placeholder
             * @default
             */
            placeholder?: string;
            /**
             * Rows
             * @default 1
             */
            rows?: number;
            /** Type */
            type: string;
        } & {
            [key: string]: unknown;
        };
        /** EvidenceItem */
        EvidenceItem: {
            /**
             * Hasoriginal
             * @default
             */
            hasOriginal?: string;
            /**
             * Itemcount
             * @default
             */
            itemCount?: string;
            /**
             * Kind
             * @default
             */
            kind?: string;
            /**
             * Name
             * @default
             */
            name?: string;
            /**
             * Notes
             * @default
             */
            notes?: string;
            /**
             * Originaltype
             * @default
             */
            originalType?: string;
            /**
             * Pagecount
             * @default
             */
            pageCount?: string;
            /**
             * Pagerange
             * @default
             */
            pageRange?: string;
            /**
             * Purpose
             * @default
             */
            purpose?: string;
            /**
             * Source
             * @default
             */
            source?: string;
        };
        /** EvidenceRequest */
        EvidenceRequest: {
            /**
             * Casenumber
             * @default
             */
            caseNumber?: string;
            /**
             * Committeename
             * @default
             */
            committeeName?: string;
            /**
             * Copycount
             * @default 2
             */
            copyCount?: number;
            /** Evidencelist */
            evidenceList?: components["schemas"]["EvidenceItem"][];
            /**
             * Submitdate
             * @default
             */
            submitDate?: string;
            /**
             * Submittername
             * @default
             */
            submitterName?: string;
        };
        /** FormLimits */
        FormLimits: {
            /** Factslength */
            factsLength: number;
            /** Maxevidence */
            maxEvidence: number;
            /** Maxrequests */
            maxRequests: number;
            /** Requestlength */
            requestLength: number;
        };
        /** HealthResponse */
        HealthResponse: {
            /** Service */
            service: string;
            /** Status */
            status: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** LoginRequest */
        LoginRequest: {
            /** Password */
            password: string;
            /** Username */
            username: string;
        };
        /** LoginResponse */
        LoginResponse: {
            /** Access Token */
            access_token: string;
            /** Expires At */
            expires_at: number;
            /**
             * Token Type
             * @constant
             */
            token_type: "bearer";
            user: components["schemas"]["UserResponse"];
        };
        /** ProvinceCatalogEntry */
        ProvinceCatalogEntry: {
            /** Documents */
            documents: {
                [key: string]: string | null;
            };
            forms?: components["schemas"]["ProvinceForms"] | null;
            /** Name */
            name: string;
            /** Slug */
            slug: string;
            /** Source Url */
            source_url: string;
        } & {
            [key: string]: unknown;
        };
        /** ProvinceCatalogResponse */
        ProvinceCatalogResponse: {
            /** Items */
            items: components["schemas"]["ProvinceCatalogEntry"][];
        };
        /** ProvinceForms */
        ProvinceForms: {
            /** Applicationfields */
            applicationFields: string[];
            /** Evidencefields */
            evidenceFields: string[];
            /** Fielddefinitions */
            fieldDefinitions: {
                [key: string]: components["schemas"]["DocumentFieldDefinition"];
            };
            limits: components["schemas"]["FormLimits"];
            /** Version */
            version: number;
        } & {
            [key: string]: unknown;
        };
        /** QuestionRequest */
        QuestionRequest: {
            /** History */
            history?: components["schemas"]["ChatMessage"][];
            /** Question */
            question: string;
        };
        /** UserResponse */
        UserResponse: {
            /** Id */
            id: string;
            /**
             * Role
             * @enum {string}
             */
            role: "user" | "admin";
            /** Username */
            username: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    ai_status_api_ai_status_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AIStatusResponse"];
                };
            };
        };
    };
    ask_api_ask_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuestionRequest"];
            };
        };
        responses: {
            /** @description UTF-8 streamed answer */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    login_api_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LoginResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    logout_api_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    me_api_auth_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
        };
    };
    create_user_api_auth_users_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateUserRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_province_documents_api_province_documents_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProvinceCatalogResponse"];
                };
            };
        };
    };
    generate_province_application_api_province_documents__slug__application_generate_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                slug: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ApplicationRequest"];
            };
        };
        responses: {
            /** @description Generated Word document */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": string;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    generate_province_evidence_api_province_documents__slug__evidence_generate_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                slug: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EvidenceRequest"];
            };
        };
        responses: {
            /** @description Generated Word document */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": string;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
}
