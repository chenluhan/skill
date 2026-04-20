#!/usr/bin/swift

import AppKit
import Foundation
import PDFKit
import Vision

struct OCRLine: Codable {
    let pageNumber: Int
    let text: String
    let confidence: Double
    let boundingBox: [Double]
}

struct OCRPage: Codable {
    let pageNumber: Int
    let text: String
    let lines: [OCRLine]
}

struct OCRPayload: Codable {
    let engine: String
    let strategy: String
    let pageCount: Int
    let confidence: Double
    let warnings: [String]
    let rawText: String
    let pages: [OCRPage]
}

enum OCRFailure: Error {
    case missingArgument
    case loadFailed
    case renderFailed(Int)
}

func renderPage(_ page: PDFPage, scale: CGFloat) -> CGImage? {
    let bounds = page.bounds(for: .mediaBox)
    let targetSize = NSSize(
        width: max(bounds.width * scale, 1),
        height: max(bounds.height * scale, 1)
    )
    let image = page.thumbnail(of: targetSize, for: .mediaBox)
    var proposedRect = NSRect(origin: .zero, size: image.size)
    return image.cgImage(forProposedRect: &proposedRect, context: nil, hints: nil)
}

func sortLines(_ lhs: OCRLine, _ rhs: OCRLine) -> Bool {
    let leftY = lhs.boundingBox[1] + lhs.boundingBox[3]
    let rightY = rhs.boundingBox[1] + rhs.boundingBox[3]
    if abs(leftY - rightY) > 0.02 {
        return leftY > rightY
    }
    return lhs.boundingBox[0] < rhs.boundingBox[0]
}

func recognizePage(_ page: PDFPage, pageNumber: Int) throws -> OCRPage {
    guard let image = renderPage(page, scale: 2.4) else {
        throw OCRFailure.renderFailed(pageNumber)
    }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    if #available(macOS 13.0, *) {
        request.automaticallyDetectsLanguage = true
    }

    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    try handler.perform([request])

    let observations = (request.results ?? []).compactMap { observation -> OCRLine? in
        guard let candidate = observation.topCandidates(1).first else {
            return nil
        }
        let box = observation.boundingBox
        return OCRLine(
            pageNumber: pageNumber,
            text: candidate.string.trimmingCharacters(in: .whitespacesAndNewlines),
            confidence: Double(candidate.confidence),
            boundingBox: [
                Double(box.minX),
                Double(box.minY),
                Double(box.width),
                Double(box.height),
            ]
        )
    }
    .filter { !$0.text.isEmpty }
    .sorted(by: sortLines)

    let pageText = observations.map(\.text).joined(separator: "\n")
    return OCRPage(pageNumber: pageNumber, text: pageText, lines: observations)
}

do {
    guard CommandLine.arguments.count > 1 else {
        throw OCRFailure.missingArgument
    }

    let path = CommandLine.arguments[1]
    guard let document = PDFDocument(url: URL(fileURLWithPath: path)) else {
        throw OCRFailure.loadFailed
    }

    var warnings: [String] = []
    var pages: [OCRPage] = []
    var confidenceValues: [Double] = []

    for index in 0..<document.pageCount {
        guard let page = document.page(at: index) else {
            warnings.append("PDF page \(index + 1) could not be loaded.")
            continue
        }

        do {
            let result = try recognizePage(page, pageNumber: index + 1)
            pages.append(result)
            confidenceValues.append(contentsOf: result.lines.map(\.confidence))
        } catch {
            warnings.append("OCR failed on page \(index + 1): \(error.localizedDescription)")
        }
    }

    let rawText = pages.map(\.text).filter { !$0.isEmpty }.joined(separator: "\n\n")
    if rawText.isEmpty {
        warnings.append("Vision OCR did not recover any readable text.")
    }

    let overallConfidence: Double
    if confidenceValues.isEmpty {
        overallConfidence = 0.0
    } else {
        overallConfidence = confidenceValues.reduce(0.0, +) / Double(confidenceValues.count)
    }

    let payload = OCRPayload(
        engine: "vision",
        strategy: "ocr",
        pageCount: document.pageCount,
        confidence: overallConfidence,
        warnings: warnings,
        rawText: rawText,
        pages: pages
    )

    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .withoutEscapingSlashes]
    let data = try encoder.encode(payload)
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data("\n".utf8))
} catch {
    let payload = OCRPayload(
        engine: "vision",
        strategy: "ocr",
        pageCount: 0,
        confidence: 0.0,
        warnings: [String(describing: error)],
        rawText: "",
        pages: []
    )
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .withoutEscapingSlashes]
    if let data = try? encoder.encode(payload) {
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data("\n".utf8))
    }
    Foundation.exit(1)
}
