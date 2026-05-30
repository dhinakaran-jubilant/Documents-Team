import React, { useState, useRef, useEffect } from 'react';
import Layout from './Layout';
import config from './config';

const formatIndianCurrency = (val) => {
    if (!val && val !== 0) return '';
    let cleaned = String(val).replace(/[^0-9.]/g, '');
    let parts = cleaned.split('.');
    let integerPart = parts[0];
    let decimalPart = parts.length > 1 ? '.' + parts[1].slice(0, 2) : '';
    if (!integerPart) return decimalPart;
    let lastThree = integerPart.substring(integerPart.length - 3);
    let otherNumbers = integerPart.substring(0, integerPart.length - 3);
    if (otherNumbers !== '') {
        lastThree = ',' + lastThree;
    }
    let formattedInteger = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ",") + lastThree;
    return formattedInteger + decimalPart;
};

const toTitleCase = (str) => {
    if (!str) return '';
    return str.toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
};

const LENDER_OPTIONS = [
    'JUBILANT CAPITAL',
    'EASY CREDIT SOLUTION',
    'SURGE CAPITAL SOLUTIONS',
    'FORTUNE ENTERPRISES',
    'GROWTH CAPITAL',
    'ROHIT ENTERPRISES',
    'SATHYAM CREDIT SOLUTION',
    'SHRINITHA ASSOCIATES',
    'S. BALAKRISHNAN',
    'Mrs. SUDHAKAR NIRMALA',
    'S.NANDHINI DEVI',
    'SUDHAKAR SIVARAMAN (HUF)',
    'S. SUDHAKAR',
    'NEXUS CAPITAL',
    'SRI GURUDEV ENTERPRISES',
    'SENTHIL VADIVEL. A.J.',
    'Maps Enterprises',
    'ASCEND SOLUTIONS',
    'Veerappan Marudhamani HUF',
    'A. SINGARAVALLI',
    'J SENTHIL VADIVEL HUF',
    'Dinesh HUF',
    'C A PRASANTH',
    'C. VAITHYALINGAM',
    'S. Bharathi',
    'SHARVIL ENTERPRISES'
];

const Documat = ({ user, onLogout, onTabChange }) => {
    const [step, setStep] = useState(1);
    const [selectedType, setSelectedType] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorPopup, setErrorPopup] = useState(null);
    const [formData, setFormData] = useState({
        companyName: '',
        companyAddress: '',
        proprietorName: '',
        proprietorTitle: 'Mr.',
        loanDate: '',
        emiStartDate: '',
        proprietorPan: '',
        fatherOfProprietor: '',
        period: '',
        noOfPeriod: '',
        place: '',
        accountNumber: '',
        ifsc: '',
        bankName: '',
        branch: '',
        pincode: '',
        interest: '18',
        loanAmount: '',
        lenderName: 'JUBILANT CAPITAL',
        repayment: '',
        signatureValid: false,
    });
    const [joinees, setJoinees] = useState([]);
    const [loans, setLoans] = useState([
        { lenderName: 'JUBILANT CAPITAL', loanAmount: '', repayment: '' }
    ]);
    const [processingGuarantors, setProcessingGuarantors] = useState({});
    const [isBankProcessing, setIsBankProcessing] = useState(false);
    const [openDropdownIdx, setOpenDropdownIdx] = useState(null);
    const [dropdownDirection, setDropdownDirection] = useState({});

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (openDropdownIdx !== null) {
                const dropdownElement = document.getElementById(`lender-dropdown-${openDropdownIdx}`);
                if (dropdownElement && !dropdownElement.contains(event.target)) {
                    setOpenDropdownIdx(null);
                }
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [openDropdownIdx]);

    useEffect(() => {
        const fetchBankDetails = async () => {
            const cleanIfsc = (formData.ifsc || '').trim().toUpperCase();
            if (cleanIfsc && cleanIfsc.length === 11) {
                try {
                    const response = await fetch(`${config.API_BASE_URL}/api/ifsc/${cleanIfsc}`);
                    if (response.ok) {
                        const data = await response.json();
                        const pincodeMatch = data.ADDRESS ? data.ADDRESS.match(/\d{6}/) : null;

                        setFormData(prev => ({
                            ...prev,
                            bankName: data.BANK || prev.bankName,
                            branch: data.BRANCH || prev.branch,
                            pincode: (pincodeMatch ? pincodeMatch[0] : prev.pincode)
                        }));
                    }
                } catch (error) {
                    console.error("Failed to fetch bank details:", error);
                }
            }
        };

        fetchBankDetails();
    }, [formData.ifsc]);

    const options = ['Individual', 'Proprietor', 'Propriterix', 'Partnership', 'Private Limited'];

    const typeConfig = {
        'Individual': { icon: 'person', desc: 'Personal', color: 'blue' },
        'Proprietor': { icon: 'store', desc: 'Business Owner', color: 'emerald' },
        'Propriterix': { icon: 'face_3', desc: 'Female Proprietor', color: 'rose' },
        'Partnership': { icon: 'groups', desc: 'Joint Venture', color: 'amber' },
        'Private Limited': { icon: 'business', desc: 'Corporate', color: 'indigo' }
    };

    const colorClasses = {
        blue: { bg: 'bg-blue-600', text: 'text-blue-500', hoverBg: 'group-hover:bg-blue-300/20', hoverBorder: 'hover:border-blue-300', darkHoverBg: 'dark:group-hover:bg-blue-900/30', darkHoverBorder: 'dark:hover:border-blue-500/50', shadow: 'shadow-blue-600/30', border: 'border-blue-600', activeBg: 'bg-blue-600/5' },
        emerald: { bg: 'bg-emerald-600', text: 'text-emerald-500', hoverBg: 'group-hover:bg-emerald-300/20', hoverBorder: 'hover:border-emerald-300', darkHoverBg: 'dark:group-hover:bg-emerald-900/30', darkHoverBorder: 'dark:hover:border-emerald-500/50', shadow: 'shadow-emerald-600/30', border: 'border-emerald-600', activeBg: 'bg-emerald-600/5' },
        rose: { bg: 'bg-rose-600', text: 'text-rose-500', hoverBg: 'group-hover:bg-rose-300/20', hoverBorder: 'hover:border-rose-300', darkHoverBg: 'dark:group-hover:bg-rose-900/30', darkHoverBorder: 'dark:hover:border-rose-500/50', shadow: 'shadow-rose-600/30', border: 'border-rose-600', activeBg: 'bg-rose-600/5' },
        amber: { bg: 'bg-amber-600', text: 'text-amber-500', hoverBg: 'group-hover:bg-amber-300/20', hoverBorder: 'hover:border-amber-300', darkHoverBg: 'dark:group-hover:bg-amber-900/30', darkHoverBorder: 'dark:hover:border-amber-500/50', shadow: 'shadow-amber-600/30', border: 'border-amber-600', activeBg: 'bg-amber-600/5' },
        indigo: { bg: 'bg-indigo-600', text: 'text-indigo-500', hoverBg: 'group-hover:bg-indigo-300/20', hoverBorder: 'hover:border-indigo-300', darkHoverBg: 'dark:group-hover:bg-indigo-900/30', darkHoverBorder: 'dark:hover:border-indigo-500/50', shadow: 'shadow-indigo-600/30', border: 'border-indigo-600', activeBg: 'bg-indigo-600/5' }
    };

    const handleSelect = (option) => {
        setSelectedType(option);
        setTimeout(() => setStep(2), 300); // Small delay for visual feedback
    };

    const handleBackToSelection = () => {
        setStep(1);
        setTimeout(() => {
            setSelectedType(null);
            setFormData({
                companyName: '',
                companyAddress: '',
                proprietorName: '',
                loanDate: '',
                emiStartDate: '',
                proprietorPan: '',
                fatherOfProprietor: '',
                period: '',
                noOfPeriod: '',
                place: '',
                accountNumber: '',
                ifsc: '',
                bankName: '',
                branch: '',
                pincode: '',
                interest: '18',
                loanAmount: '',
                lenderName: 'JUBILANT CAPITAL',
                repayment: '',
                signatureValid: false,
            });
            setJoinees([]);
            setLoans([
                { lenderName: 'JUBILANT CAPITAL', loanAmount: '', repayment: '' }
            ]);
            setOpenDropdownIdx(null);
            setDropdownDirection({});
        }, 300); // Allow fade animation to complete before clearing selection
    };

    const handleSubmit = async (e) => {
        if (e) e.preventDefault();

        // Validation
        const fieldLabels = {
            proprietorName: 'Proprietor Name',
            loanDate: 'Loan Date',
            place: 'Place',
        };
        const required = ['proprietorName', 'loanDate', 'place'];
        const missing = required.filter(field => !formData[field]);

        let loansMissing = false;
        loans.forEach((loan) => {
            if (!loan.lenderName || !loan.loanAmount || !loan.repayment) {
                loansMissing = true;
            }
        });

        if (missing.length > 0 || loansMissing) {
            const missingLabels = missing.map(field => fieldLabels[field] || field);
            if (loansMissing) {
                missingLabels.push('Lender Name, Principal, and Repayment for all added loans');
            }
            setErrorPopup({
                title: 'Required Fields Missing',
                message: `Please complete all mandatory fields to generate documents:\n• ${missingLabels.join('\n• ')}`
            });
            return;
        }

        // Validate Pincode length (must be exactly 6 digits)
        if (formData.pincode && formData.pincode.length !== 6) {
            setErrorPopup({
                title: 'Invalid Pincode',
                message: 'Branch Pincode must be exactly 6 digits.'
            });
            return;
        }

        // Validate Primary PAN length (must be exactly 10 characters)
        if (formData.proprietorPan && formData.proprietorPan.length !== 10) {
            setErrorPopup({
                title: 'Invalid PAN Card',
                message: 'Borrower Firm PAN must be exactly 10 alphanumeric characters.'
            });
            return;
        }

        // Validate Guarantor PAN length (must be exactly 10 characters)
        for (let i = 0; i < joinees.length; i++) {
            const j = joinees[i];
            if (j.pan && j.pan.length !== 10) {
                setErrorPopup({
                    title: 'Invalid Guarantor PAN',
                    message: `Guarantor #${i + 1} (${j.name || 'Unnamed'}) PAN must be exactly 10 alphanumeric characters.`
                });
                return;
            }
        }

        // Validate IFSC length (must be exactly 11 characters)
        if (formData.ifsc && formData.ifsc.length !== 11) {
            setErrorPopup({
                title: 'Invalid IFSC Code',
                message: 'IFSC Code must be exactly 11 alphanumeric characters.'
            });
            return;
        }

        // Clean payload values by stripping commas
        const fullProprietorName = `${formData.proprietorTitle || 'Mr.'} ${formData.proprietorName || ''}`.trim();
        const cleanedFormData = {
            ...formData,
            proprietorName: fullProprietorName,
            lenderName: loans[0]?.lenderName || 'JUBILANT CAPITAL',
            loanAmount: (loans[0]?.loanAmount || '').replace(/,/g, ''),
            repayment: (loans[0]?.repayment || '').replace(/,/g, '')
        };

        const cleanedLoans = loans.map(l => ({
            lenderName: l.lenderName,
            loanAmount: (l.loanAmount || '').replace(/,/g, ''),
            repayment: (l.repayment || '').replace(/,/g, '')
        }));

        const cleanedJoinees = joinees.map(j => ({
            ...j,
            name: `${j.title || 'Mr.'} ${j.name || ''}`.trim()
        }));

        setIsSubmitting(true);

        try {
            const response = await fetch(`${config.API_BASE_URL}/api/generate-promissory-note`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    formData: cleanedFormData,
                    loans: cleanedLoans,
                    joinees: cleanedJoinees,
                }),
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error || 'Failed to generate documents');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;

            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `Documents_${formData.proprietorName.replace(/\s+/g, '_')}.zip`;
            if (contentDisposition && contentDisposition.includes('filename=')) {
                const parts = contentDisposition.split('filename=');
                if (parts[1]) filename = parts[1].replace(/["']/g, '');
            }

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error generating documents:', error);
            setErrorPopup({
                title: 'Generation Failed',
                message: error.message || 'An unexpected error occurred during document assembly.'
            });
        } finally {
            setIsSubmitting(false);
        }
    };


    const handleProprietorUpload = async (e) => {
        const selectedFiles = Array.from(e.target.files);
        if (selectedFiles.length === 0) return;

        setIsProcessing(true);

        // Local state copies to track asynchronous changes synchronously inside the loop
        let currentFormData = { ...formData };
        let currentJoinees = [...joinees];

        for (const file of selectedFiles) {
            const data = new FormData();
            data.append('file', file);

            try {
                const response = await fetch(`${config.API_BASE_URL}/extract-pdf`, {
                    method: 'POST',
                    body: data,
                });
                const result = await response.json();

                if (result.success && result.data) {
                    const docType = result.data.document_type;

                    const isPdf = file.name.toLowerCase().endsWith('.pdf');

                    // 1. If it's a PDF (GST), it's always the Proprietor
                    if (isPdf && selectedType === 'Proprietor') {
                        currentFormData = {
                            ...currentFormData,
                            companyName: result.data.trade_name || currentFormData.companyName,
                            proprietorPan: result.data.pan_number || currentFormData.proprietorPan,
                            companyAddress: result.data.business_address ? toTitleCase(result.data.business_address) : currentFormData.companyAddress,
                            place: result.data.district || currentFormData.place,
                            signatureValid: result.data.signature_valid !== undefined ? result.data.signature_valid : currentFormData.signatureValid,
                        };
                        continue;
                    }

                    // 2. Extract and clean names for Aadhaar/PAN image routing
                    const legalName = result.data.name || result.data.legal_name || '';
                    const cleanName = legalName
                        .split(/\s+/)
                        .filter(part => part.replace(/\./g, '').length > 1)
                        .join(' ')
                        .toUpperCase();

                    const fatherNameExtracted = result.data.father_name ? result.data.father_name.toUpperCase() : '';

                    if (!cleanName) continue; // Skip if no name extracted

                    // 3. Determine if it belongs to the Proprietor or a Guarantor
                    let isProprietorDoc = true;

                    if (currentFormData.proprietorName) {
                        const cleanPropName = currentFormData.proprietorName
                            .split(/\s+/)
                            .filter(part => part.replace(/\./g, '').length > 1)
                            .join(' ')
                            .toUpperCase();

                        // If proprietor name is set and differs from document name, it's a Guarantor doc
                        if (cleanName !== cleanPropName) {
                            isProprietorDoc = false;
                        }
                    }

                    if (isProprietorDoc) {
                        // Update Proprietor details
                        const isProprietorAadhaar = selectedType === 'Proprietor' && docType === 'aadhaar';
                        currentFormData = {
                            ...currentFormData,
                            proprietorTitle: result.data.gender ? (result.data.gender === 'MALE' ? 'Mr.' : 'Mrs.') : currentFormData.proprietorTitle,
                            companyName: result.data.trade_name || currentFormData.companyName,
                            proprietorName: cleanName || currentFormData.proprietorName,
                            fatherOfProprietor: fatherNameExtracted || currentFormData.fatherOfProprietor,
                            companyAddress: isProprietorAadhaar ? currentFormData.companyAddress : (result.data.business_address ? toTitleCase(result.data.business_address) : currentFormData.companyAddress),
                            place: isProprietorAadhaar ? currentFormData.place : (result.data.district || currentFormData.place),
                            signatureValid: result.data.signature_valid !== undefined ? result.data.signature_valid : currentFormData.signatureValid,
                        };
                        if (docType === 'pan' && result.data.pan_number) {
                            currentFormData.proprietorPan = result.data.pan_number.toUpperCase();
                        }
                    } else {
                        // Update or Add a Guarantor Card!
                        let guarantorIndex = currentJoinees.findIndex(j => {
                            const cleanJName = (j.name || '')
                                .split(/\s+/)
                                .filter(part => part.replace(/\./g, '').length > 1)
                                .join(' ')
                                .toUpperCase();
                            return cleanJName && cleanName === cleanJName;
                        });

                        if (guarantorIndex === -1) {
                            // Create a new guarantor card!
                            const newGuarantor = {
                                name: cleanName,
                                title: result.data.gender ? (result.data.gender === 'MALE' ? 'Mr.' : 'Mrs.') : 'Mr.',
                                father: fatherNameExtracted,
                                pan: docType === 'pan' && result.data.pan_number ? result.data.pan_number.toUpperCase() : '',
                                address: docType === 'aadhaar' && (result.data.business_address || result.data.address) ? toTitleCase(result.data.business_address || result.data.address) : ''
                            };
                            currentJoinees.push(newGuarantor);
                        } else {
                            // Merge details into existing guarantor card!
                            currentJoinees[guarantorIndex] = {
                                ...currentJoinees[guarantorIndex],
                                name: cleanName || currentJoinees[guarantorIndex].name,
                                title: result.data.gender ? (result.data.gender === 'MALE' ? 'Mr.' : 'Mrs.') : currentJoinees[guarantorIndex].title,
                                father: fatherNameExtracted || currentJoinees[guarantorIndex].father,
                                pan: docType === 'pan' && result.data.pan_number ? result.data.pan_number.toUpperCase() : currentJoinees[guarantorIndex].pan,
                                address: docType === 'aadhaar' && (result.data.business_address || result.data.address) ? toTitleCase(result.data.business_address || result.data.address) : currentJoinees[guarantorIndex].address
                            };
                        }
                    }
                } else {
                    console.error(result.error);
                    alert(`Failed to process ${file.name}: ${result.error}`);
                }
            } catch (error) {
                console.error(`Error extracting ${file.name}:`, error);
                alert(`Error connecting to server while processing ${file.name}`);
            }
        }

        // Apply all batched updates to React state
        setFormData(currentFormData);
        setJoinees(currentJoinees);
        setIsProcessing(false);
        e.target.value = '';
    };

    const handleGuarantorUpload = async (e, index) => {
        const selectedFiles = Array.from(e.target.files);
        if (selectedFiles.length === 0) return;

        setIsProcessing(true);
        setProcessingGuarantors(prev => ({ ...prev, [index]: true }));
        const updatedJoinees = [...joinees];

        try {
            for (const file of selectedFiles) {
                const uploadFormData = new FormData();
                uploadFormData.append('file', file);

                try {
                    const response = await fetch(`${config.API_BASE_URL}/extract-pdf`, {
                        method: 'POST',
                        body: uploadFormData,
                    });
                    const result = await response.json();

                    if (result.success && result.data) {
                        const data = result.data;

                        if (data.document_type === 'aadhaar') {
                            const legalName = data.legal_name || data.name || '';
                            const cleanName = legalName
                                .split(/\s+/)
                                .filter(part => part.replace(/\./g, '').length > 1)
                                .join(' ');

                            updatedJoinees[index].name = cleanName ? cleanName.toUpperCase() : updatedJoinees[index].name;

                            if (data.father_name) {
                                updatedJoinees[index].father = data.father_name.toUpperCase();
                            }
                            if (data.gender) {
                                updatedJoinees[index].title = data.gender === 'MALE' ? 'Mr.' : 'Mrs.';
                            }
                            const addr = data.business_address || data.address;
                            if (addr) {
                                updatedJoinees[index].address = toTitleCase(addr);
                            }
                        } else if (data.document_type === 'pan') {
                            if (data.pan_number) {
                                updatedJoinees[index].pan = data.pan_number.toUpperCase();
                            }
                            const panName = data.legal_name || data.name;
                            if (!updatedJoinees[index].name && panName) {
                                const cleanName = panName
                                    .split(/\s+/)
                                    .filter(part => part.replace(/\./g, '').length > 1)
                                    .join(' ');
                                updatedJoinees[index].name = cleanName ? cleanName.toUpperCase() : updatedJoinees[index].name;
                            }
                            if (!updatedJoinees[index].father && data.father_name) {
                                updatedJoinees[index].father = data.father_name.toUpperCase();
                            }
                        }
                    } else {
                        console.error(result.error);
                        alert(`Failed to process ${file.name}: ${result.error}`);
                    }
                } catch (error) {
                    console.error(`Error uploading guarantor document ${file.name}:`, error);
                    alert(`Error connecting to server while processing ${file.name}`);
                }
            }
            setJoinees(updatedJoinees);
        } finally {
            setProcessingGuarantors(prev => {
                const next = { ...prev };
                delete next[index];
                return next;
            });
            setIsProcessing(false);
            e.target.value = '';
        }
    };

    const handleBankUpload = async (e) => {
        const selectedFiles = Array.from(e.target.files);
        if (selectedFiles.length === 0) return;

        setIsBankProcessing(true);

        try {
            const file = selectedFiles[0];
            const uploadFormData = new FormData();
            uploadFormData.append('file', file);

            const response = await fetch(`${config.API_BASE_URL}/extract-bank`, {
                method: 'POST',
                body: uploadFormData,
            });
            const result = await response.json();

            if (result.success && result.data) {
                const { ifsc, account_number } = result.data;
                setFormData(prev => ({
                    ...prev,
                    ifsc: ifsc ? ifsc.toUpperCase() : prev.ifsc,
                    accountNumber: account_number ? account_number.toUpperCase() : prev.accountNumber
                }));
            } else {
                console.error(result.error);
                alert(`Failed to process bank document: ${result.error}`);
            }
        } catch (error) {
            console.error("Error uploading bank document:", error);
            alert("Error connecting to server while processing bank document");
        } finally {
            setIsBankProcessing(false);
            e.target.value = '';
        }
    };

    return (
        <Layout user={user} onLogout={onLogout} onTabChange={onTabChange} onTabClick={(tab) => tab === 'documat' && handleBackToSelection()} activeTab="documat">
            <main className="flex-1 bg-slate-50 dark:bg-[#101822] px-10 pt-10 pb-6 transition-colors duration-300">
                <div className="flex flex-col min-h-full">
                    {/* Header Section */}
                    <div className="flex flex-col items-start text-left gap-2 mb-10">
                        {step === 1 && (
                            <div className="animate-in fade-in slide-in-from-top-4 duration-500">
                                <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight">Documat</h1>
                                <p className="text-sm font-medium text-slate-500 max-w-2xl mt-2">Select an entity type to initiate onboarding and securely extract data from business documents.</p>
                            </div>
                        )}
                        {step === 2 && (
                            <div className="flex items-center gap-2 text-blue-500 font-bold text-[11px] uppercase tracking-widest mb-1">
                                <span className="hover:text-blue-400 cursor-pointer transition-colors" onClick={handleBackToSelection}>Documat</span>
                                <span className="material-symbols-outlined text-sm opacity-50 text-slate-500">chevron_right</span>
                                <span className="text-slate-400">{selectedType}</span>
                            </div>
                        )}
                    </div>

                    {step === 1 ? (
                        /* Selection Grid */
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            {options.map((option) => {
                                const isEnabled = option === 'Proprietor';
                                return (
                                <button
                                    key={option}
                                    onClick={() => isEnabled && handleSelect(option)}
                                    disabled={!isEnabled}
                                    className={`group flex flex-col items-start p-8 rounded-[32px] border-2 transition-all duration-500 text-left relative overflow-hidden ${
                                        !isEnabled
                                            ? 'border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/30 opacity-50 cursor-not-allowed select-none'
                                            : selectedType === option
                                                ? `${colorClasses[typeConfig[option].color].border} bg-white dark:bg-[#0f172b] shadow-2xl ${colorClasses[typeConfig[option].color].shadow} scale-[1.02] cursor-pointer`
                                                : `border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0f172b] ${colorClasses[typeConfig[option].color].hoverBorder} ${colorClasses[typeConfig[option].color].darkHoverBorder} hover:bg-slate-50 dark:hover:bg-slate-800/20 cursor-pointer`
                                    }`}
                                >
                                    {/* Coming Soon badge for disabled options */}
                                    {!isEnabled && (
                                        <span className="absolute top-4 right-4 text-[9px] font-black uppercase tracking-[0.15em] px-2.5 py-1 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400">
                                            Coming Soon
                                        </span>
                                    )}

                                    {/* Icon */}
                                    <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-6 transition-all duration-500 ${selectedType === option
                                        ? `${colorClasses[typeConfig[option].color].bg} text-white`
                                        : `bg-slate-100 dark:bg-slate-800 text-slate-400 ${isEnabled ? `${colorClasses[typeConfig[option].color].hoverBg} ${colorClasses[typeConfig[option].color].darkHoverBg} group-hover:${colorClasses[typeConfig[option].color].text}` : ''}`
                                        }`}>
                                        <span className="material-symbols-outlined text-3xl">
                                            {typeConfig[option].icon}
                                        </span>
                                    </div>

                                    <div className="space-y-1">
                                        <h3 className={`text-xl font-black tracking-tight transition-colors ${selectedType === option ? 'text-slate-900 dark:text-white' : 'text-slate-700 dark:text-slate-300'
                                            }`}>
                                            {option}
                                        </h3>
                                        <p className="text-[12px] font-bold uppercase tracking-[0.2em] text-slate-400">
                                            {typeConfig[option].desc}
                                        </p>
                                    </div>

                                    <div className={`absolute -bottom-6 -right-6 w-24 h-24 rounded-full transition-all duration-700 blur-3xl ${selectedType === option ? `${colorClasses[typeConfig[option].color].bg}/20` : 'bg-transparent'
                                        }`}></div>
                                </button>
                                );
                            })}
                        </div>
                    ) : (
                        /* Step 2: Document Form */
                        <div className="flex-1 flex flex-col items-center animate-in fade-in slide-in-from-right-12 duration-700">
                            <div className="w-full max-w-6xl bg-white dark:bg-[#0f172b] rounded-[2rem] border border-slate-200 dark:border-slate-800 p-12 shadow-2xl relative overflow-hidden transition-colors duration-300">
                                {/* Form Header */}
                                <div className="flex items-center justify-between mb-12">
                                    <div className="flex items-center gap-6">
                                        <div className={`w-16 h-16 rounded-2xl ${colorClasses[typeConfig[selectedType].color].bg} text-white flex items-center justify-center shadow-2xl ${colorClasses[typeConfig[selectedType].color].shadow}`}>
                                            <span className="material-symbols-outlined text-3xl">{typeConfig[selectedType].icon}</span>
                                        </div>
                                        <div>
                                            <h2 className="text-2xl font-black text-slate-900 dark:text-white leading-none mb-2 uppercase">{selectedType} Onboarding</h2>
                                        </div>
                                    </div>
                                </div>

                                {/* Onboarding Details Section */}
                                <div className="mb-10 p-8 rounded-[2rem] bg-slate-50/80 dark:bg-[#030712]/50 border border-slate-100 dark:border-slate-800/50 relative overflow-hidden">
                                    <div className="space-y-8">
                                        {/* Company & Proprietor Details */}
                                        <div className="space-y-6 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20 relative overflow-hidden">
                                            {isProcessing && (
                                                <div className="absolute inset-0 w-full h-full left-0 top-0 z-30 !mt-0 flex flex-col items-center justify-center bg-white/75 dark:bg-[#0f172b]/75 backdrop-blur-md transition-all duration-300 rounded-2xl">
                                                    <div className="flex flex-col items-center gap-3">
                                                        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                                                        <span className="text-[11px] font-black uppercase tracking-[0.2em] text-blue-500 animate-pulse">Extracting Proprietor Details...</span>
                                                    </div>
                                                </div>
                                            )}
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Proprietor Details</h3>
                                                    <p className="text-[11px] text-slate-500 mt-1">Specify proprietor details or upload Aadhaar/PAN/GST card</p>
                                                </div>
                                                <label className="w-8 h-8 rounded-xl flex items-center justify-center text-blue-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-all cursor-pointer relative" title="Upload Aadhaar / PAN / GST">
                                                    <input
                                                        type="file"
                                                        accept="image/*,.pdf"
                                                        multiple
                                                        onChange={handleProprietorUpload}
                                                        className="hidden"
                                                    />
                                                    <span className="material-symbols-outlined text-lg">upload_file</span>
                                                </label>
                                            </div>

                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Borrower Firm Name <span className="text-red-500">*</span></label>
                                                    <input type="text" placeholder="Enter borrower firm name" value={formData.companyName} onChange={(e) => setFormData({ ...formData, companyName: e.target.value })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Proprietor Name <span className="text-red-500">*</span></label>
                                                    <div className="flex gap-2">
                                                        <select
                                                            value={formData.proprietorTitle || 'Mr.'}
                                                            onChange={(e) => setFormData({ ...formData, proprietorTitle: e.target.value })}
                                                            className="appearance-none pl-4 pr-8 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium min-w-[80px] bg-[size:16px] bg-[position:right_10px_center] bg-no-repeat bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%20fill%3D%22none%22%3E%3Cpath%20d%3D%22M7%209l3%203%203-3%22%20stroke%3D%22%236b7280%22%20stroke-width%3D%221.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%2F%3E%3C%2Fsvg%3E')]"
                                                        >
                                                            <option value="Mr.">Mr.</option>
                                                            <option value="Mrs.">Mrs.</option>
                                                        </select>
                                                        <input
                                                            type="text"
                                                            placeholder="Enter proprietor name"
                                                            value={formData.proprietorName}
                                                            onChange={(e) => setFormData({ ...formData, proprietorName: e.target.value })}
                                                            className="flex-1 px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                                        />
                                                    </div>
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Father of Proprietor <span className="text-red-500">*</span></label>
                                                    <input type="text" placeholder="Enter father's name" value={formData.fatherOfProprietor} onChange={(e) => setFormData({ ...formData, fatherOfProprietor: e.target.value })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Borrower Firm PAN <span className="text-red-500">*</span></label>
                                                    <input type="text" maxLength={10} placeholder="XXXXX0000X" value={formData.proprietorPan} onChange={(e) => setFormData({ ...formData, proprietorPan: e.target.value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase().slice(0, 10) })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all uppercase" />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Borrower Firm Address <span className="text-red-500">*</span></label>
                                                    <textarea rows="1" placeholder="Enter borrower firm address" value={formData.companyAddress} onChange={(e) => setFormData({ ...formData, companyAddress: toTitleCase(e.target.value) })} className="w-full px-6 py-[14px] rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none min-h-[100px]" />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Place <span className="text-red-500">*</span></label>
                                                    <input type="text" placeholder="City/Town" value={formData.place} onChange={(e) => setFormData({ ...formData, place: e.target.value })} className="w-full px-6 py-[15px] rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                                                </div>
                                            </div>
                                        </div>

                                        <hr className="border-slate-200 dark:border-slate-800/50" />

                                        {/* Loan Core Details */}
                                        <div className="space-y-6 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20 relative">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Lender & Loan Details</h3>
                                                    <p className="text-[11px] text-slate-500 mt-1">Specify lender firm names, principal amounts, and repayments</p>
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={() => {
                                                        setLoans([...loans, { lenderName: 'JUBILANT CAPITAL', loanAmount: '', repayment: '' }]);
                                                        setOpenDropdownIdx(null);
                                                    }}
                                                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold uppercase tracking-wider text-[10px] text-white bg-blue-600 shadow-md shadow-blue-600/20 hover:-translate-y-0.5 active:scale-95 transition-all cursor-pointer"
                                                >
                                                    <span className="material-symbols-outlined text-sm">add</span>
                                                    Add New
                                                </button>
                                            </div>
                                            {loans.map((loan, idx) => (
                                                <div key={idx} className="space-y-4">
                                                    {idx > 0 && (
                                                        <>
                                                            <hr className="space-y-2 pt-2" />
                                                            <div className="flex items-center justify-between pt-2">
                                                                <h4 className="text-xs font-black uppercase tracking-wider text-slate-500">Loan #{idx + 1}</h4>
                                                                <button
                                                                    type="button"
                                                                    onClick={() => {
                                                                        setLoans(loans.filter((_, i) => i !== idx));
                                                                        setOpenDropdownIdx(null);
                                                                    }}
                                                                    className="w-8 h-8 rounded-xl flex items-center justify-center text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-400/10 transition-all cursor-pointer"
                                                                >
                                                                    <span className="material-symbols-outlined text-lg">delete</span>
                                                                </button>
                                                            </div>
                                                        </>
                                                    )}
                                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                                        <div className="space-y-2">
                                                            <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Lender Firm Name <span className="text-red-500">*</span></label>
                                                            <div className="relative" id={`lender-dropdown-${idx}`}>
                                                                <button
                                                                    type="button"
                                                                    onClick={(e) => {
                                                                        if (openDropdownIdx === idx) {
                                                                            setOpenDropdownIdx(null);
                                                                        } else {
                                                                            const rect = e.currentTarget.getBoundingClientRect();
                                                                            const spaceBelow = window.innerHeight - rect.bottom;
                                                                            const shouldOpenUpward = spaceBelow < 260;
                                                                            setDropdownDirection(prev => ({
                                                                                ...prev,
                                                                                [idx]: shouldOpenUpward ? 'top' : 'bottom'
                                                                            }));
                                                                            setOpenDropdownIdx(idx);
                                                                        }
                                                                    }}
                                                                    className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all flex items-center justify-between text-left uppercase font-semibold text-sm cursor-pointer"
                                                                >
                                                                    <span className={loan.lenderName ? "text-slate-950 dark:text-slate-100 font-medium" : "text-slate-400 dark:text-slate-500"}>
                                                                        {loan.lenderName || "Select Lender Firm Name"}
                                                                    </span>
                                                                    <span className={`material-symbols-outlined text-slate-400 dark:text-slate-500 transition-transform duration-200 ${openDropdownIdx === idx ? 'rotate-180' : ''}`}>
                                                                        expand_more
                                                                    </span>
                                                                </button>

                                                                {openDropdownIdx === idx && (
                                                                    <div className={`absolute z-50 w-full bg-white dark:bg-[#0f172b]/95 border border-slate-200 dark:border-slate-800/80 rounded-2xl shadow-xl backdrop-blur-xl overflow-hidden dropdown-fade-in ${dropdownDirection[idx] === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'
                                                                        }`}>
                                                                        <div className="max-h-60 overflow-y-auto scrollbar-slim py-2">
                                                                            {LENDER_OPTIONS.map((option) => (
                                                                                <button
                                                                                    key={option}
                                                                                    type="button"
                                                                                    onClick={() => {
                                                                                        const updated = [...loans];
                                                                                        updated[idx].lenderName = option;
                                                                                        setLoans(updated);
                                                                                        setOpenDropdownIdx(null);
                                                                                    }}
                                                                                    className={`w-full px-6 py-3 text-left uppercase text-xs font-semibold tracking-wider transition-all duration-150 flex items-center justify-between cursor-pointer ${loan.lenderName === option
                                                                                        ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 font-bold border-l-4 border-blue-500 pl-5'
                                                                                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60 border-l-4 border-transparent'
                                                                                        }`}
                                                                                >
                                                                                    <span>{option}</span>
                                                                                    {loan.lenderName === option && (
                                                                                        <span className="material-symbols-outlined text-blue-500 dark:text-blue-400 text-sm font-bold">check</span>
                                                                                    )}
                                                                                </button>
                                                                            ))}
                                                                        </div>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>
                                                        <div className="space-y-2">
                                                            <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Principal <span className="text-red-500">*</span></label>
                                                            <input
                                                                type="text"
                                                                placeholder="Enter principal amount"
                                                                value={loan.loanAmount}
                                                                onChange={(e) => {
                                                                    const updated = [...loans];
                                                                    updated[idx].loanAmount = formatIndianCurrency(e.target.value);
                                                                    setLoans(updated);
                                                                }}
                                                                className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                                            />
                                                        </div>
                                                        <div className="space-y-2">
                                                            <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Repayment <span className="text-red-500">*</span></label>
                                                            <input
                                                                type="text"
                                                                placeholder="Enter repayment amount"
                                                                value={loan.repayment}
                                                                onChange={(e) => {
                                                                    const updated = [...loans];
                                                                    updated[idx].repayment = formatIndianCurrency(e.target.value);
                                                                    setLoans(updated);
                                                                }}
                                                                className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                                            />
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>

                                        <hr className="border-slate-200 dark:border-slate-800/50" />

                                        {/* Loan Details */}
                                        <div className="space-y-6 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20 relative overflow-hidden">
                                            <div>
                                                <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Loan Terms & Schedule</h3>
                                                <p className="text-[11px] text-slate-500 mt-1">Specify loan dates, repayment frequency, and interest rates</p>
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Loan Date <span className="text-red-500">*</span></label>
                                                    <input type="date" value={formData.loanDate} onChange={(e) => setFormData({ ...formData, loanDate: e.target.value })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all [color-scheme:light] dark:[color-scheme:dark]" />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">EMI Start Date <span className="text-red-500">*</span></label>
                                                    <input type="date" value={formData.emiStartDate} onChange={(e) => setFormData({ ...formData, emiStartDate: e.target.value })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all [color-scheme:light] dark:[color-scheme:dark]" />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Period Type <span className="text-red-500">*</span></label>
                                                    <div className="relative">
                                                        <select value={formData.period} onChange={(e) => setFormData({ ...formData, period: e.target.value })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none pr-12">
                                                            <option value="" disabled>Select Period</option>
                                                            <option value="daily">Daily</option>
                                                            <option value="weekly">Weekly</option>
                                                            <option value="biweekly">Biweekly</option>
                                                            <option value="bimonthly">Bimonthly</option>
                                                            <option value="monthly">Monthly</option>
                                                        </select>
                                                        <div className="absolute inset-y-0 right-0 flex items-center pr-4 pointer-events-none text-slate-400">
                                                            <span className="material-symbols-outlined">expand_more</span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">No of Period <span className="text-red-500">*</span></label>
                                                    <input type="number" min="0" placeholder="Enter number" value={formData.noOfPeriod} onChange={(e) => setFormData({ ...formData, noOfPeriod: e.target.value.replace(/[^0-9]/g, '') })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Interest (%) <span className="text-red-500">*</span></label>
                                                    <input type="number" min="0" step="0.1" value={formData.interest} onChange={(e) => setFormData({ ...formData, interest: e.target.value.replace(/[^0-9.]/g, '') })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                                                </div>
                                            </div>
                                        </div>

                                        <hr className="border-slate-200 dark:border-slate-800/50" />

                                        {/* Banking Details */}
                                        <div className="space-y-6 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20 relative overflow-hidden">
                                            {isBankProcessing && (
                                                <div className="absolute inset-0 w-full h-full left-0 top-0 z-30 !mt-0 flex flex-col items-center justify-center bg-white/75 dark:bg-[#0f172b]/75 backdrop-blur-md transition-all duration-300 rounded-2xl">
                                                    <div className="flex flex-col items-center gap-3">
                                                        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                                                        <span className="text-[11px] font-black uppercase tracking-[0.2em] text-blue-500 animate-pulse">Extracting Bank Details...</span>
                                                    </div>
                                                </div>
                                            )}
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Banking Details</h3>
                                                    <p className="text-[11px] text-slate-500 mt-1">Specify bank account details or upload cancelled cheque</p>
                                                </div>
                                                <label className="w-8 h-8 rounded-xl flex items-center justify-center text-blue-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-all cursor-pointer relative" title="Upload Cheque / Passbook">
                                                    <input
                                                        type="file"
                                                        accept="image/*,.pdf"
                                                        onChange={handleBankUpload}
                                                        className="hidden"
                                                    />
                                                    <span className="material-symbols-outlined text-lg">upload_file</span>
                                                </label>
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Account Number <span className="text-red-500">*</span></label>
                                                    <input type="text" placeholder="Enter account number" value={formData.accountNumber} onChange={(e) => setFormData({ ...formData, accountNumber: e.target.value })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">IFSC <span className="text-red-500">*</span></label>
                                                    <input type="text" maxLength={11} placeholder="Enter IFSC code" value={formData.ifsc} onChange={(e) => setFormData({ ...formData, ifsc: e.target.value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase().slice(0, 11) })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all uppercase" />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Bank Name <span className="text-red-500">*</span></label>
                                                    <input type="text" placeholder="Enter bank name" value={formData.bankName} onChange={(e) => setFormData({ ...formData, bankName: e.target.value })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Branch <span className="text-red-500">*</span></label>
                                                    <input type="text" placeholder="Enter branch name" value={formData.branch} onChange={(e) => setFormData({ ...formData, branch: e.target.value })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                                                </div>
                                                <div className="space-y-2">
                                                    <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Branch Pincode <span className="text-red-500">*</span></label>
                                                    <input type="text" maxLength={6} placeholder="000000" value={formData.pincode} onChange={(e) => setFormData({ ...formData, pincode: e.target.value.replace(/\D/g, '').slice(0, 6) })} className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all" />
                                                </div>
                                            </div>
                                        </div>

                                        <hr className="border-slate-200 dark:border-slate-800/50" />

                                        {/* Joinee Section */}
                                        <div className="space-y-6">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Guarantor Information</h3>
                                                    <p className="text-[11px] text-slate-500 mt-1">Add details of any guarantors</p>
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={() => setJoinees([...joinees, { name: '', title: 'Mr.', father: '', pan: '', address: '' }])}
                                                    className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold uppercase tracking-wider text-[10px] text-white bg-blue-600 shadow-md shadow-blue-600/20 hover:-translate-y-0.5 active:scale-95 transition-all cursor-pointer`}
                                                >
                                                    <span className="material-symbols-outlined text-sm">add</span>
                                                    Add Guarantor
                                                </button>
                                            </div>

                                            {joinees.map((joinee, index) => (
                                                <div key={index} className="space-y-6 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20 relative overflow-hidden">
                                                    {processingGuarantors[index] && (
                                                        <div className="absolute inset-0 w-full h-full left-0 top-0 z-30 !mt-0 flex flex-col items-center justify-center bg-white/75 dark:bg-[#0f172b]/75 backdrop-blur-md transition-all duration-300 rounded-2xl">
                                                            <div className="flex flex-col items-center gap-3">
                                                                <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                                                                <span className="text-[11px] font-black uppercase tracking-[0.2em] text-blue-500 animate-pulse">Extracting...</span>
                                                            </div>
                                                        </div>
                                                    )}
                                                    <div className="flex items-center justify-between">
                                                        <h4 className="text-xs font-black uppercase tracking-wider text-slate-500">Guarantor #{index + 1}</h4>
                                                        <div className="flex items-center gap-2">
                                                            <label className="w-8 h-8 rounded-xl flex items-center justify-center text-blue-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-all cursor-pointer relative" title="Upload Aadhaar / PAN">
                                                                <input
                                                                    type="file"
                                                                    multiple
                                                                    accept="image/*,.pdf"
                                                                    onChange={(e) => handleGuarantorUpload(e, index)}
                                                                    className="hidden"
                                                                />
                                                                <span className="material-symbols-outlined text-lg">upload_file</span>
                                                            </label>
                                                            <button
                                                                type="button"
                                                                onClick={() => setJoinees(joinees.filter((_, i) => i !== index))}
                                                                className="w-8 h-8 rounded-xl flex items-center justify-center text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-400/10 transition-all cursor-pointer"
                                                            >
                                                                <span className="material-symbols-outlined text-lg">delete</span>
                                                            </button>
                                                        </div>
                                                    </div>
                                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                        <div className="space-y-2">
                                                            <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Guarantor Name <span className="text-red-500">*</span></label>
                                                            <div className="flex gap-2">
                                                                <select
                                                                    value={joinee.title || 'Mr.'}
                                                                    onChange={(e) => {
                                                                        const updated = [...joinees];
                                                                        updated[index].title = e.target.value;
                                                                        setJoinees(updated);
                                                                    }}
                                                                    className="appearance-none pl-4 pr-8 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all font-medium min-w-[80px] bg-[size:16px] bg-[position:right_10px_center] bg-no-repeat bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2020%2020%22%20fill%3D%22none%22%3E%3Cpath%20d%3D%22M7%209l3%203%203-3%22%20stroke%3D%22%236b7280%22%20stroke-width%3D%221.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%2F%3E%3C%2Fsvg%3E')]"
                                                                >
                                                                    <option value="Mr.">Mr.</option>
                                                                    <option value="Mrs.">Mrs.</option>
                                                                </select>
                                                                <input
                                                                    type="text"
                                                                    placeholder="Enter joinee name"
                                                                    value={joinee.name}
                                                                    onChange={(e) => {
                                                                        const updated = [...joinees];
                                                                        updated[index].name = e.target.value;
                                                                        setJoinees(updated);
                                                                    }}
                                                                    className="flex-1 px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                                                />
                                                            </div>
                                                        </div>
                                                        <div className="space-y-2">
                                                            <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Guarantor Father <span className="text-red-500">*</span></label>
                                                            <input
                                                                type="text"
                                                                placeholder="Enter father's name"
                                                                value={joinee.father}
                                                                onChange={(e) => {
                                                                    const updated = [...joinees];
                                                                    updated[index].father = e.target.value;
                                                                    setJoinees(updated);
                                                                }}
                                                                className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                                            />
                                                        </div>
                                                        <div className="space-y-2">
                                                            <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Guarantor PAN <span className="text-red-500">*</span></label>
                                                            <input
                                                                type="text"
                                                                maxLength={10}
                                                                placeholder="XXXXX0000X"
                                                                value={joinee.pan}
                                                                onChange={(e) => {
                                                                    const updated = [...joinees];
                                                                    updated[index].pan = e.target.value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase().slice(0, 10);
                                                                    setJoinees(updated);
                                                                }}
                                                                className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all uppercase"
                                                            />
                                                        </div>
                                                        <div className="space-y-2">
                                                            <label className="block text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 ml-1">Guarantor Address <span className="text-red-500">*</span></label>
                                                            <input
                                                                type="text"
                                                                placeholder="Enter address"
                                                                value={joinee.address}
                                                                onChange={(e) => {
                                                                    const updated = [...joinees];
                                                                    updated[index].address = e.target.value;
                                                                    setJoinees(updated);
                                                                }}
                                                                className="w-full px-6 py-4 rounded-2xl bg-white dark:bg-[#0f172b] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                                                            />
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                {/* Action Buttons */}
                                <div className="flex items-center justify-end gap-4 pt-6 border-t border-slate-100 dark:border-slate-800/50">
                                    <button
                                        onClick={handleBackToSelection}
                                        className="px-8 py-4 rounded-xl font-black uppercase tracking-widest text-[11px] text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/40 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-all active:scale-95 cursor-pointer"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleSubmit}
                                        disabled={isSubmitting}
                                        className={`px-10 py-4 rounded-xl font-black uppercase tracking-widest text-[11px] text-white ${colorClasses[typeConfig[selectedType].color].bg} shadow-lg ${colorClasses[typeConfig[selectedType].color].shadow} hover:-translate-y-0.5 transition-all active:scale-95 cursor-pointer disabled:opacity-50`}
                                    >
                                        {isSubmitting ? 'Generating...' : 'Submit'}
                                    </button>
                                </div>

                                {/* Decorative Background Accent */}
                                <div className={`pointer-events-none absolute -top-24 -right-24 w-64 h-64 rounded-full blur-[100px] opacity-20 ${colorClasses[typeConfig[selectedType].color].bg}`}></div>
                            </div>
                        </div>
                    )}

                    {/* Footer */}
                    <footer className="mt-12 pt-6 border-t border-slate-200 dark:border-slate-800/50 text-center text-[12px] font-bold tracking-[0.1em] text-slate-500">
                        <p>
                            All rights reserved &copy; 2026 @ Jubilant Capital. Designed and Developed by{' '}
                            <a href="mailto:dhinakaran.s@jubilantenterprises.in" className="text-blue-500 hover:underline">
                                Dhinakaran Sekar
                            </a>
                        </p>
                    </footer>
                </div>
            </main>

            {/* Custom Error Popup Modal */}
            {errorPopup && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md transition-all duration-300 animate-fade-in">
                    <div className="w-full max-w-md overflow-hidden rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0f172b] shadow-2xl p-8 transform scale-100 transition-all duration-300">
                        <div className="flex items-center gap-4 text-red-500 dark:text-red-400 mb-4">
                            <div className="w-12 h-12 rounded-2xl bg-red-500/10 flex items-center justify-center">
                                <span className="material-symbols-outlined text-2xl">warning</span>
                            </div>
                            <div>
                                <h3 className="text-sm font-black uppercase tracking-wider text-slate-800 dark:text-white">{errorPopup.title || 'Error'}</h3>
                                <p className="text-[11px] font-medium tracking-wide text-slate-400 mt-0.5">Validation failed</p>
                            </div>
                        </div>

                        <div className="space-y-3 mt-4">
                            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-semibold whitespace-pre-line">
                                {errorPopup.message}
                            </p>
                        </div>

                        <div className="mt-8 flex justify-end">
                            <button
                                type="button"
                                onClick={() => setErrorPopup(null)}
                                className="px-6 py-3 rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-bold uppercase tracking-wider text-[10px] hover:-translate-y-0.5 active:scale-95 transition-all cursor-pointer shadow-lg shadow-slate-950/20"
                            >
                                Dismiss
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </Layout>
    );
};

export default Documat;
